"""Targeted unit tests for normalizers, reference DB, and report builder."""

from __future__ import annotations

from datetime import date

from physoca.engine.evaluator import evaluate_patient
from physoca.models.medication import MedicationInput
from physoca.models.patient import HistoryFlags, LabValues, Patient
from physoca.normalize.diagnoses import normalize_diagnoses
from physoca.normalize.doses import normalize_dose
from physoca.normalize.names import clean_drug_name, normalize_medication
from physoca.reference.db import lookup_drug_in_db
from physoca.report.build import build_review_report


def test_clean_drug_name_preserves_calcium() -> None:
    assert clean_drug_name("Calcium Carbonate 500 mg") == "calcium carbonate"
    assert clean_drug_name("Pantoprazole Sodium 40mg EC") == "pantoprazole"


def test_normalize_diagnoses_undotted_icd10() -> None:
    res = normalize_diagnoses(["K210", "G3183", "GERD", ""])
    assert "K21.0" in res
    assert "G31.83" in res


def test_normalize_dose_variants() -> None:
    mg, per_day, _ = normalize_dose(250.0, "mcg", "daily", prn=False)
    assert mg == 0.25
    assert per_day == 1.0

    mg2, per_day2, _ = normalize_dose(5.0, "mg", "bid", prn=True)
    assert mg2 == 10.0
    assert per_day2 == 2.0

    mg3, per_day3, _ = normalize_dose(1.0, "g", "tid", prn=False)
    assert mg3 == 3000.0
    assert per_day3 == 3.0


def test_lookup_drug_in_db_known_and_unknown() -> None:
    assert lookup_drug_in_db("pantoprazole") is not None
    assert lookup_drug_in_db("nonexistent_xyz_drug_123") is None


def test_normalize_medication_and_report_fr() -> None:
    patient = Patient(
        age=78,
        sex="female",
        weight_kg=62.0,
        setting="community",
        review_date=date(2026, 11, 13),
        diagnoses=["K210", "G31.83"],
        labs=LabValues(serum_creatinine_umol_l=95.0, a1c_percent=7.2),
        history=HistoryFlags(falls_past_year=True, cognitive_decline=True),
    )
    meds_in = [
        MedicationInput(
            name="Pantoprazole",
            dose=40.0,
            unit="mg",
            frequency="daily",
            start_date=date(2026, 1, 1),
        ),
        MedicationInput(
            name="Lorazepam",
            dose=1.0,
            unit="mg",
            frequency="qhs",
            prn=True,
            start_date=date(2026, 2, 1),
        ),
    ]
    meds = []
    for m in meds_in:
        meds.extend(normalize_medication(m, patient))
    assert len(meds) == 2

    result = evaluate_patient(patient, meds_in, lang="fr")
    report = build_review_report(patient, meds_in, lang="fr")
    assert result.patient.age == 78
    assert report.patient_summary.age == 78
