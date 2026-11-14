"""Unit tests for normalization modules."""

from datetime import date

import pytest

from physoca.models.medication import MedicationInput
from physoca.models.patient import Patient, Sex
from physoca.normalize.diagnoses import normalize_diagnoses
from physoca.normalize.doses import normalize_dose, parse_frequency
from physoca.normalize.durations import compute_duration_days
from physoca.normalize.names import clean_drug_name, normalize_medication
from physoca.normalize.renal import compute_cockcroft_gault, compute_egfr_ckd_epi_2021


def test_renal_ckd_epi_and_cg() -> None:
    egfr_f = compute_egfr_ckd_epi_2021(90.0, 75, Sex.FEMALE)
    egfr_m = compute_egfr_ckd_epi_2021(90.0, 75, Sex.MALE)
    assert egfr_f is not None and egfr_m is not None
    assert egfr_m > egfr_f
    assert compute_egfr_ckd_epi_2021(90.0, 75, Sex.UNSPECIFIED) is None

    crcl = compute_cockcroft_gault(90.0, 75, 65.0, Sex.FEMALE)
    assert crcl is not None and crcl > 0
    assert compute_cockcroft_gault(90.0, 75, None, Sex.FEMALE) is None


def test_duration_leap_year_and_missing() -> None:
    assert compute_duration_days(None, date(2026, 11, 13)) is None
    assert compute_duration_days(date(2024, 2, 28), date(2024, 3, 1)) == 2
    assert compute_duration_days(date(2026, 12, 1), date(2026, 11, 13)) == 0


def test_dose_and_frequency() -> None:
    assert parse_frequency("bid") == 2.0
    assert parse_frequency("q8h") == 3.0
    assert parse_frequency("qhs") == 1.0
    assert parse_frequency(None, prn=True) is None
    mg_day, dpd, disp = normalize_dose(125.0, "mcg", "daily")
    assert mg_day == pytest.approx(0.125)
    assert dpd == 1.0
    assert disp == "125 mcg daily"


def test_diagnoses_normalization() -> None:
    dx = normalize_diagnoses(["K21.0", "gerd", "Dementia", "unknown_dx"])
    assert "K21.0" in dx
    assert "F03" in dx
    assert "G30" in dx
    assert "UNKNOWN_DX" in dx


def test_medication_name_and_expansion() -> None:
    p = Patient(age_years=72, sex=Sex.MALE, review_date=date(2026, 11, 13))
    assert clean_drug_name("Ativan 1mg") == "ativan"
    rows = normalize_medication(MedicationInput(name="Tramacet", dose=37.5, unit="mg", frequency="tid"), p)
    assert len(rows) == 2
    assert {r.ingredient for r in rows} == {"tramadol", "acetaminophen"}

    unknown = normalize_medication(MedicationInput(name="MysteryDrugX"), p)
    assert len(unknown) == 1
    assert not unknown[0].recognized
    assert "unrecognized" in unknown[0].flags
