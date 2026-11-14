"""Top-level review report model."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from physoca.models.finding import (
    AnticholinergicSummary,
    AuditEntry,
    FallRiskSummary,
    Finding,
    NeedsDataItem,
    OmissionFinding,
    SourceRef,
)
from physoca.models.medication import NormalizedMedication
from physoca.models.patient import CareSetting


class PatientSummary(BaseModel):
    age_years: int
    sex: str
    care_setting: CareSetting
    review_date: date
    egfr_ckd_epi_2021: float | None = None
    egfr_source: str | None = None
    crcl_cockcroft_gault: float | None = None
    a1c_percent: float | None = None
    individualized_a1c_target_percent: float | None = None
    suggested_a1c_target_note: str | None = None
    clinical_frailty_scale: int | None = None
    diagnoses_count: int = 0
    missing_fields: list[str] = Field(default_factory=list)


class VersionInfo(BaseModel):
    physoca_version: str
    pack_name: str
    pack_version: str
    dpd_extract_date: str
    rxnorm_release: str
    version_banner: str


class ReviewReport(BaseModel):
    """Complete deterministic medication review output."""

    schema_version: str = "1.0.0"
    language: str = "en"
    intended_use: str
    patient_summary: PatientSummary
    medications: list[NormalizedMedication] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    anticholinergic: AnticholinergicSummary = Field(default_factory=AnticholinergicSummary)
    fall_risk: FallRiskSummary = Field(default_factory=FallRiskSummary)
    omissions: list[OmissionFinding] = Field(default_factory=list)
    needs_data: list[NeedsDataItem] = Field(default_factory=list)
    audit_trace: list[AuditEntry] = Field(default_factory=list)
    cited_sources: list[SourceRef] = Field(default_factory=list)
    attributions: list[str] = Field(default_factory=list)
    versions: VersionInfo
