from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from dateutil.parser import parse

from app.models import CompRecord, TargetAsset, RentEstimate, WaterfallStep


ANNUAL_RENT_GROWTH = Decimal("0.03")
VINTAGE_ADJ_PER_YEAR = Decimal("0.0015")
CLEAR_HEIGHT_ADJ_PER_FOOT = Decimal("0.01")
SIZE_ADJ_FACTOR = Decimal("0.08")


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_date(value: str) -> date:
    return parse(str(value)).date()


def years_between(start: str, end: str) -> Decimal:
    signed = parse_date(start)
    as_of = date.fromisoformat(end)
    days = (as_of - signed).days
    return Decimal(days) / Decimal("365")


def weighted_average(values: list[Decimal], weights: list[Decimal]) -> Decimal:
    total_weight = sum(weights)

    if total_weight == 0:
        raise ValueError("Cannot compute weighted average with zero total weight.")

    return sum(v * w for v, w in zip(values, weights)) / total_weight


def adjusted_rent_for_comp(comp: CompRecord, target: TargetAsset) -> Decimal:
    rent = comp.rent_psf_yr

    years = years_between(comp.signed_date, target.as_of)
    rent = rent * ((Decimal("1") + ANNUAL_RENT_GROWTH) ** years)

    vintage_delta = Decimal(target.year_built - comp.year_built)
    rent = rent * (Decimal("1") + vintage_delta * VINTAGE_ADJ_PER_YEAR)

    size_ratio = Decimal(comp.lease_sf) / Decimal(target.total_sf)
    size_delta = (size_ratio - Decimal("1")) * SIZE_ADJ_FACTOR
    rent = rent * (Decimal("1") + size_delta)

    clear_delta = Decimal(target.clear_height_ft - comp.clear_height_ft)
    rent = rent * (Decimal("1") + clear_delta * CLEAR_HEIGHT_ADJ_PER_FOOT)

    return money(rent)


def estimate_market_rent(
    target: TargetAsset,
    used_comps: list[CompRecord],
    dropped_comps: list[CompRecord],
) -> RentEstimate:
    if not used_comps:
        raise ValueError("No usable comps available after ingestion.")

    weights = [comp.confidence for comp in used_comps]

    raw_base = weighted_average(
        [comp.rent_psf_yr for comp in used_comps],
        weights,
    )

    after_time = weighted_average(
        [
            money(
                comp.rent_psf_yr
                * ((Decimal("1") + ANNUAL_RENT_GROWTH) ** years_between(comp.signed_date, target.as_of))
            )
            for comp in used_comps
        ],
        weights,
    )

    after_vintage = weighted_average(
        [
            money(
                comp.rent_psf_yr
                * ((Decimal("1") + ANNUAL_RENT_GROWTH) ** years_between(comp.signed_date, target.as_of))
                * (Decimal("1") + Decimal(target.year_built - comp.year_built) * VINTAGE_ADJ_PER_YEAR)
            )
            for comp in used_comps
        ],
        weights,
    )

    after_size = weighted_average(
        [
            money(
                comp.rent_psf_yr
                * ((Decimal("1") + ANNUAL_RENT_GROWTH) ** years_between(comp.signed_date, target.as_of))
                * (Decimal("1") + Decimal(target.year_built - comp.year_built) * VINTAGE_ADJ_PER_YEAR)
                * (
                    Decimal("1")
                    + ((Decimal(comp.lease_sf) / Decimal(target.total_sf)) - Decimal("1")) * SIZE_ADJ_FACTOR
                )
            )
            for comp in used_comps
        ],
        weights,
    )

    final_adjusted_rents = [
        adjusted_rent_for_comp(comp, target)
        for comp in used_comps
    ]

    final_estimate = weighted_average(final_adjusted_rents, weights)
    point = money(final_estimate)

    dispersion = Decimal(
        str(median([abs(rent - point) for rent in final_adjusted_rents]))
    )
    band_width = max(Decimal("0.35"), dispersion)

    avg_confidence = weighted_average(weights, weights)

    waterfall = [
        WaterfallStep(
            step="Base weighted rent",
            before=money(raw_base),
            after=money(raw_base),
            delta=Decimal("0.00"),
            rationale="Confidence-weighted average of surviving lease comps before adjustments.",
        ),
        WaterfallStep(
            step="Time adjustment",
            before=money(raw_base),
            after=money(after_time),
            delta=money(after_time - raw_base),
            rationale=f"Rents trended to {target.as_of} using a declared {ANNUAL_RENT_GROWTH * 100}% annual rent growth assumption.",
        ),
        WaterfallStep(
            step="Vintage adjustment",
            before=money(after_time),
            after=money(after_vintage),
            delta=money(after_vintage - after_time),
            rationale="Older comps are adjusted upward when inferior to the target's 2008 vintage; newer comps are adjusted downward.",
        ),
        WaterfallStep(
            step="Size adjustment",
            before=money(after_vintage),
            after=money(after_size),
            delta=money(after_size - after_vintage),
            rationale="Larger leases generally price lower per square foot; smaller leases are adjusted downward relative to the target size.",
        ),
        WaterfallStep(
            step="Clear height adjustment",
            before=money(after_size),
            after=point,
            delta=money(point - after_size),
            rationale=f"Comps below the target's {target.clear_height_ft} ft clear height receive upward adjustment; superior clear height receives downward adjustment.",
        ),
    ]

    return RentEstimate(
        point_estimate_psf_yr=point,
        low_psf_yr=money(point - band_width),
        high_psf_yr=money(point + band_width),
        confidence=money(avg_confidence),
        waterfall=waterfall,
        used_comps=used_comps,
        dropped_comps=dropped_comps,
    )
