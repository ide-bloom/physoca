"""Hypothesis property-based tests."""

from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from physoca.models.medication import MedicationInput
from physoca.models.patient import Patient, Sex
from physoca.normalize.durations import compute_duration_days
from physoca.normalize.names import clean_drug_name
from physoca.normalize.renal import compute_egfr_ckd_epi_2021
from physoca.report.build import build_review_report


@given(st.text(min_size=1, max_size=50))
def test_clean_drug_name_idempotent(raw: str) -> None:
    once = clean_drug_name(raw)
    twice = clean_drug_name(once)
    assert once == twice


@given(
    scr1=st.floats(min_value=40.0, max_value=300.0),
    delta=st.floats(min_value=1.0, max_value=100.0),
    age=st.integers(min_value=18, max_value=100),
)
def test_egfr_monotonic_in_creatinine(scr1: float, delta: float, age: int) -> None:
    e1 = compute_egfr_ckd_epi_2021(scr1, age, Sex.FEMALE)
    e2 = compute_egfr_ckd_epi_2021(scr1 + delta, age, Sex.FEMALE)
    assert e1 is not None and e2 is not None
    assert e1 >= e2


@given(
    start=st.dates(min_value=date(2000, 1, 1), max_value=date(2026, 11, 1)),
    days=st.integers(min_value=0, max_value=2000),
)
def test_duration_exact_days(start: date, days: int) -> None:
    review = start + timedelta(days=days)
    assert compute_duration_days(start, review) == days


@settings(max_examples=30, deadline=None)
@given(
    age=st.integers(min_value=0, max_value=120),
    med_names=st.lists(st.sampled_from(["Pantoprazole", "Lorazepam", "Digoxin", "UnknownX"]), max_size=5),
)
def test_report_never_raises_on_valid_input(age: int, med_names: list[str]) -> None:
    p = Patient(age_years=age, sex=Sex.FEMALE)
    meds = [MedicationInput(name=n) for n in med_names]
    report = build_review_report(p, meds)
    assert report.patient_summary.age_years == age
