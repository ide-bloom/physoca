"""Assemble a ReviewReport from evaluation output."""

from __future__ import annotations

from physoca.config import (
    DPD_ATTRIBUTION,
    INTENDED_USE_STATEMENT,
    INTENDED_USE_STATEMENT_FR,
    RXNORM_ATTRIBUTION,
    Settings,
)
from physoca.engine.evaluator import evaluate_patient
from physoca.models.finding import SourceRef
from physoca.models.medication import MedicationInput
from physoca.models.patient import Patient
from physoca.models.report import PatientSummary, ReviewReport, VersionInfo
from physoca.version import __version__


def build_review_report(
    patient: Patient,
    medications: list[MedicationInput],
    lang: str = "en",
    include_drafts: bool = False,
) -> ReviewReport:
    """Evaluate patient and medications and assemble a complete ReviewReport."""
    settings = Settings.from_env()
    ev = evaluate_patient(patient, medications, lang=lang, include_drafts=include_drafts)

    missing: list[str] = []
    if patient.weight_kg is None:
        missing.append("weight_kg")
    if ev.egfr is None:
        missing.append("egfr_ml_min_1_73")
    if patient.a1c_percent is None:
        missing.append("a1c_percent")
    if patient.clinical_frailty_scale is None:
        missing.append("clinical_frailty_scale")
    if not patient.diagnoses:
        missing.append("diagnoses (empty)")

    suggested_a1c_note: str | None = None
    if (
        patient.individualized_a1c_target_percent is None
        and patient.clinical_frailty_scale is not None
    ):
        cfs = patient.clinical_frailty_scale
        if cfs <= 3:
            suggested_a1c_note = "Suggested Diabetes Canada target (unverified): <=7.0% (low hypoglycemia risk) or 7.1-7.5% (insulin/sulfonylurea)."
        elif cfs <= 5:
            suggested_a1c_note = "Suggested Diabetes Canada target (unverified): <=7.5% (low hypoglycemia risk) or 7.1-8.0% (insulin/sulfonylurea)."
        else:
            suggested_a1c_note = "Suggested Diabetes Canada target (unverified): <=8.0% (low hypoglycemia risk) or 7.5-8.5% (insulin/sulfonylurea)."

    summary = PatientSummary(
        age_years=patient.age_years,
        sex=patient.sex.value,
        care_setting=patient.care_setting,
        review_date=patient.review_date,
        egfr_ckd_epi_2021=ev.egfr,
        egfr_source=ev.egfr_source,
        crcl_cockcroft_gault=ev.crcl,
        a1c_percent=patient.a1c_percent,
        individualized_a1c_target_percent=patient.individualized_a1c_target_percent,
        suggested_a1c_target_note=suggested_a1c_note,
        clinical_frailty_scale=patient.clinical_frailty_scale,
        diagnoses_count=len(ev.diagnoses),
        missing_fields=missing,
    )

    seen_src: set[tuple[str, str]] = set()
    cited: list[SourceRef] = []
    for f in ev.findings:
        for s in f.sources:
            key = (s.id, s.locator)
            if key not in seen_src:
                seen_src.add(key)
                cited.append(s)
    for o in ev.omissions:
        for s in o.sources:
            key = (s.id, s.locator)
            if key not in seen_src:
                seen_src.add(key)
                cited.append(s)

    banner = (
        f"physoca {__version__} | rules {ev.pack_version} | "
        f"DPD {settings.dpd_extract_date} | RxNorm {settings.rxnorm_release}"
    )
    versions = VersionInfo(
        physoca_version=__version__,
        pack_name=ev.pack_name,
        pack_version=ev.pack_version,
        dpd_extract_date=settings.dpd_extract_date,
        rxnorm_release=settings.rxnorm_release,
        version_banner=banner,
    )

    intended_use = INTENDED_USE_STATEMENT_FR if lang == "fr" else INTENDED_USE_STATEMENT

    return ReviewReport(
        language=lang,
        intended_use=intended_use,
        patient_summary=summary,
        medications=ev.medications,
        findings=ev.findings,
        anticholinergic=ev.anticholinergic,
        fall_risk=ev.fall_risk,
        omissions=ev.omissions,
        needs_data=ev.needs_data,
        audit_trace=ev.audit_trace,
        cited_sources=cited,
        attributions=[DPD_ATTRIBUTION, RXNORM_ATTRIBUTION],
        versions=versions,
    )
