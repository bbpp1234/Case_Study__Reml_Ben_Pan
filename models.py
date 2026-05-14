from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field


class TargetAsset(BaseModel):
    address: str
    submarket: str
    total_sf: int = Field(gt=0)
    year_built: int = Field(gt=1800)
    clear_height_ft: int = Field(gt=0)
    as_of: str


class WaterfallStep(BaseModel):
    step: str
    before: Decimal
    after: Decimal
    delta: Decimal
    rationale: str


class CompRecord(BaseModel):
    id: str
    address: str
    submarket: str
    signed_date: str
    lease_sf: int
    term_months: int | None = None
    rent_psf_yr: Decimal | None = None
    year_built: int | None = None
    clear_height_ft: int | None = None
    source: str | None = None
    notes: str | None = None
    confidence: Decimal
    status: Literal["used", "dropped"]
    reason: str


class RentEstimate(BaseModel):
    point_estimate_psf_yr: Decimal
    low_psf_yr: Decimal
    high_psf_yr: Decimal
    confidence: Decimal
    waterfall: list[WaterfallStep]
    used_comps: list[CompRecord]
    dropped_comps: list[CompRecord]
