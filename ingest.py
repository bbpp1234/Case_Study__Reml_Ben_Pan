import hashlib
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from app.models import CompRecord, TargetAsset


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "comps_phx_industrial.csv"


SOURCE_CONFIDENCE = {
    "internal": Decimal("0.95"),
    "CBRE": Decimal("0.90"),
    "JLL": Decimal("0.88"),
    "Colliers": Decimal("0.86"),
    "Cushman": Decimal("0.84"),
    "Newmark": Decimal("0.82"),
    "broker_flyer": Decimal("0.70"),
}


ADJACENT_SUBMARKETS = {
    "Sky Harbor": {"Southwest Phoenix", "Tolleson"},
}


def stable_id(address: str, signed_date: str) -> str:
    raw = f"{address}|{signed_date}".lower().strip()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def parse_decimal(value) -> Decimal | None:
    if pd.isna(value):
        return None

    text = str(value).strip().lower()

    if text in {"", "-", "—", "undisclosed", "na", "n/a", "none"}:
        return None

    try:
        return Decimal(text.replace("$", "").replace(",", ""))
    except InvalidOperation:
        return None


def normalize_rent(raw_rent, notes: str | None) -> tuple[Decimal | None, str | None]:
    rent = parse_decimal(raw_rent)

    if rent is None:
        return None, "missing or undisclosed rent"

    note_text = (notes or "").lower()

    if "month" in note_text or "monthly" in note_text or "$/sf/month" in note_text:
        return rent * Decimal("12"), "monthly rent normalized to annual"

    return rent, None


def submarket_reason(target: TargetAsset, comp_submarket: str) -> tuple[bool, str, Decimal]:
    if comp_submarket == target.submarket:
        return True, "same submarket", Decimal("1.00")

    if comp_submarket in ADJACENT_SUBMARKETS.get(target.submarket, set()):
        return True, "adjacent submarket with lower confidence", Decimal("0.80")

    return False, "outside target market", Decimal("0.00")


def clean_int(value) -> int | None:
    if pd.isna(value):
        return None

    try:
        return int(value)
    except Exception:
        return None


def load_comps(target: TargetAsset) -> tuple[list[CompRecord], list[CompRecord]]:
    df = pd.read_csv(DATA_PATH)

    all_records = []

    for _, row in df.iterrows():
        address = str(row.get("address", "")).strip()
        signed_date = str(row.get("signed_date", "")).strip()
        source = str(row.get("source", "")).strip()
        notes = "" if pd.isna(row.get("notes")) else str(row.get("notes")).strip()

        comp_id = stable_id(address, signed_date)
        rent, rent_note = normalize_rent(row.get("rent_psf_yr"), notes)

        lease_sf = clean_int(row.get("lease_sf"))
        year_built = clean_int(row.get("year_built"))
        clear_height = clean_int(row.get("clear_height_ft"))
        term_months = clean_int(row.get("term_months"))
        submarket = str(row.get("submarket", "")).strip()

        base_confidence = SOURCE_CONFIDENCE.get(source, Decimal("0.75"))

        usable_submarket, market_reason, market_factor = submarket_reason(target, submarket)
        confidence = base_confidence * market_factor

        missing_reasons = []

        if rent is None:
            missing_reasons.append(rent_note or "missing rent")
        if lease_sf is None:
            missing_reasons.append("missing lease size")
        if year_built is None:
            missing_reasons.append("missing year built")
        if clear_height is None:
            missing_reasons.append("missing clear height")
        if not usable_submarket:
            missing_reasons.append(market_reason)

        status = "used"
        reason_parts = [market_reason]

        if rent_note:
            reason_parts.append(rent_note)
            confidence *= Decimal("0.95")

        if missing_reasons:
            status = "dropped"
            reason_parts = missing_reasons

        all_records.append(
            CompRecord(
                id=comp_id,
                address=address,
                submarket=submarket,
                signed_date=signed_date,
                lease_sf=lease_sf or 0,
                term_months=term_months,
                rent_psf_yr=rent,
                year_built=year_built,
                clear_height_ft=clear_height,
                source=source,
                notes=notes,
                confidence=confidence.quantize(Decimal("0.01")),
                status=status,
                reason="; ".join(reason_parts),
            )
        )

    used = [r for r in all_records if r.status == "used"]
    dropped = [r for r in all_records if r.status == "dropped"]

    deduped = {}
    duplicate_drops = []

    for comp in used:
        key = (comp.address.lower(), comp.signed_date)

        if key not in deduped:
            deduped[key] = comp
            continue

        existing = deduped[key]

        if comp.confidence > existing.confidence:
            duplicate_drops.append(
                existing.model_copy(
                    update={
                        "status": "dropped",
                        "reason": f"duplicate deal; kept higher-confidence source {comp.source}",
                    }
                )
            )
            deduped[key] = comp
        else:
            duplicate_drops.append(
                comp.model_copy(
                    update={
                        "status": "dropped",
                        "reason": f"duplicate deal; kept higher-confidence source {existing.source}",
                    }
                )
            )

    final_used = list(deduped.values())
    final_dropped = dropped + duplicate_drops

    return final_used, final_dropped
