"""Finding, scoring, and audit trace models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    CONSIDER = "consider"
    REVIEW = "review"
    URGENT = "urgent"

    def rank(self) -> int:
        return {"consider": 1, "review": 2, "urgent": 3}[self.value]


class TaperInfo(BaseModel):
    needed: bool = False
    abrupt_stop_risk: str = "low"
    note: str = ""


class EvidenceInfo(BaseModel):
    quality: str = "moderate"
    strength: str = "strong"
    rating_verified: bool = False
    caution: bool = False
    note: str | None = None


class SourceRef(BaseModel):
    id: str
    locator: str
    verified: bool = False


class AuditEntry(BaseModel):
    rule_id: str
    rule_version: int
    outcome: str  # matched, exempted, not_applicable, not_matched, needs_data
    matched_conditions: list[str] = Field(default_factory=list)
    exemptions_evaluated: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    renal_estimate_used: str | None = None


class Finding(BaseModel):
    """A single merged or set-based deprescribing finding."""

    rule_ids: list[str]
    title: str
    category: str
    severity: Severity
    medications: list[str]
    rationales: list[str]
    action: str
    alternatives: str | None = None
    taper: TaperInfo
    evidence: EvidenceInfo
    sources: list[SourceRef]
    monitoring_note: str = ""
    renal_note: str | None = None
    disclaimer: str = (
        "Decision support for review by a health care professional. "
        "Not a diagnosis or treatment direction."
    )


class AnticholinergicDrugScore(BaseModel):
    ingredient: str
    acb: int | None = None
    cals: int | None = None
    danish_2024: int | None = None


class AnticholinergicSummary(BaseModel):
    acb_total: int = 0
    cals_total: int = 0
    danish_2024_total: int = 0
    threshold_gte: int = 3
    scale_disagreement: bool = False
    disagreement_note: str = ""
    contributing_drugs: list[AnticholinergicDrugScore] = Field(default_factory=list)
    citation_note: str = (
        "No gold standard anticholinergic scale exists; 74% of high-potency drugs "
        "are scored inconsistently across scales (J Am Geriatr Soc 2026;74(6):1771-1784)."
    )


class FallRiskSummary(BaseModel):
    applicable: bool = False
    reason: str = ""
    classes: dict[str, list[str]] = Field(default_factory=dict)


class OmissionFinding(BaseModel):
    """Separate START-style omission finding (possible under-treatment)."""

    rule_id: str
    title: str
    category: str
    rationale: str
    action: str
    evidence: EvidenceInfo
    sources: list[SourceRef]


class NeedsDataItem(BaseModel):
    rule_id: str
    title: str
    missing_fields: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
