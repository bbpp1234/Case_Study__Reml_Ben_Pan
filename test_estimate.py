from app.ingest import load_comps
from app.estimate import estimate_market_rent
from app.models import TargetAsset


def test_market_rent_estimate_runs():
    target = TargetAsset(
        address="4150 S 51st Ave, Phoenix, AZ 85043",
        submarket="Sky Harbor",
        total_sf=145000,
        year_built=2008,
        clear_height_ft=32,
        as_of="2025-09-30",
    )

    used_comps, dropped_comps = load_comps(target)
    estimate = estimate_market_rent(target, used_comps, dropped_comps)

    assert estimate.point_estimate_psf_yr > 0
    assert estimate.low_psf_yr < estimate.point_estimate_psf_yr
    assert estimate.high_psf_yr > estimate.point_estimate_psf_yr
    assert len(estimate.waterfall) == 5
    assert estimate.waterfall[-1].after == estimate.point_estimate_psf_yr


def test_ingest_drops_bad_rows():
    target = TargetAsset(
        address="4150 S 51st Ave, Phoenix, AZ 85043",
        submarket="Sky Harbor",
        total_sf=145000,
        year_built=2008,
        clear_height_ft=32,
        as_of="2025-09-30",
    )

    used_comps, dropped_comps = load_comps(target)

    assert len(used_comps) > 0
    assert len(dropped_comps) > 0
    assert all(comp.rent_psf_yr is not None for comp in used_comps)
