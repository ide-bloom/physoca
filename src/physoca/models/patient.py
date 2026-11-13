"""Patient input model with clinical validation."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class Sex(StrEnum):
    FEMALE = "female"
    MALE = "male"
    UNSPECIFIED = "unspecified"


class CareSetting(StrEnum):
    COMMUNITY = "community"
    LONG_TERM_CARE = "long_term_care"
    HOSPITAL = "hospital"


class HistoryFlag(StrEnum):
    FALLS = "falls"
    HYPOGLYCEMIA = "hypoglycemia"
    GI_BLEED = "gi_bleed"
    DELIRIUM = "delirium"
    FAILED_PPI_DISCONTINUATION = "failed_ppi_discontinuation"
    LIFE_EXPECTANCY_LIMITED = "life_expectancy_limited"
    PALLIATIVE_CARE = "palliative_care"
    ORTHOSTATIC_HYPOTENSION = "orthostatic_hypotension"
    URINARY_RETENTION = "urinary_retention"
    CHRONIC_CONSTIPATION = "chronic_constipation"
    COGNITIVE_DECLINE = "cognitive_decline"


class Patient(BaseModel):
    """Structured patient profile for medication review."""

    age_years: int = Field(..., ge=0, le=120)
    sex: Sex = Sex.UNSPECIFIED
    weight_kg: float | None = Field(default=None, gt=10.0, le=400.0)
    height_cm: float | None = Field(default=None, gt=40.0, le=260.0)
    serum_creatinine_umol_l: float | None = Field(default=None, gt=10.0, le=2500.0)
    egfr_ml_min_1_73: float | None = Field(default=None, gt=1.0, le=200.0)
    a1c_percent: float | None = Field(default=None, gt=2.0, le=25.0)
    individualized_a1c_target_percent: float | None = Field(default=None, gt=4.0, le=15.0)
    care_setting: CareSetting = CareSetting.COMMUNITY
    clinical_frailty_scale: int | None = Field(default=None, ge=1, le=9)
    diagnoses: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    history_flags: list[HistoryFlag] = Field(default_factory=list)
    review_date: date = Field(default_factory=date.today)

    @model_validator(mode="after")
    def _check_a1c_consistency(self) -> Patient:
        if self.a1c_percent is not None and self.a1c_percent < 3.0:
            raise ValueError("a1c_percent must be at least 3.0")
        return self
