"""Medication input and normalized medication models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class MedicationInput(BaseModel):
    """Raw medication entry supplied by the user or calling system."""

    name: str = Field(..., min_length=1, max_length=200)
    din: str | None = Field(default=None, max_length=20)
    rxcui: str | None = Field(default=None, max_length=20)
    dose: float | None = Field(default=None, ge=0.0)
    unit: str | None = Field(default=None, max_length=40)
    frequency: str | None = Field(default=None, max_length=80)
    route: str | None = Field(default="oral", max_length=40)
    start_date: date | None = None
    indication: str | None = Field(default=None, max_length=200)
    prn: bool = False
    prescriber: str | None = Field(default=None, max_length=120)


class NormalizedMedication(BaseModel):
    """Medication normalized to canonical ingredient, mg/day dose, and duration."""

    original_name: str
    ingredient: str
    recognized: bool = True
    resolution_source: str = "synonym"
    din: str | None = None
    rxcui: str | None = None
    atc_codes: list[str] = Field(default_factory=list)
    class_groups: list[str] = Field(default_factory=list)
    original_dose_display: str = ""
    dose_mg_day: float | None = None
    doses_per_day: float | None = None
    route: str = "oral"
    start_date: date | None = None
    duration_days: int | None = None
    indication: str | None = None
    prn: bool = False
    flags: list[str] = Field(default_factory=list)
