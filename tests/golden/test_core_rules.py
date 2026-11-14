"""Golden tests for core rules: positive, negative, exemption, and escalation/downgrade."""

from datetime import date

from physoca.engine.evaluator import evaluate_patient
from physoca.models.medication import MedicationInput
from physoca.models.patient import CareSetting, HistoryFlag, Patient, Sex


def test_phy_gi_001_positive_negative_and_exempt() -> None:
    # Positive: > 56 days, no exemption
    p = Patient(age_years=70, sex=Sex.FEMALE, review_date=date(2026, 11, 13))
    out = evaluate_patient(p, [MedicationInput(name="Pantoprazole", start_date=date(2026, 8, 1))])
    assert any("PHY-GI-001" in f.rule_ids for f in out.findings)

    # Near-miss negative: 56 days
    out_neg = evaluate_patient(
        p, [MedicationInput(name="Pantoprazole", start_date=date(2026, 9, 18))]
    )
    assert not any("PHY-GI-001" in f.rule_ids for f in out_neg.findings)

    # Exempt: GERD (K21.0)
    p_ex = Patient(
        age_years=70, sex=Sex.FEMALE, diagnoses=["K21.0"], review_date=date(2026, 11, 13)
    )
    out_ex = evaluate_patient(
        p_ex, [MedicationInput(name="Pantoprazole", start_date=date(2026, 8, 1))]
    )
    assert not any("PHY-GI-001" in f.rule_ids for f in out_ex.findings)


def test_phy_cns_001_escalate_and_downgrade() -> None:
    # Escalate with falls -> urgent
    p_esc = Patient(age_years=75, history_flags=[HistoryFlag.FALLS], review_date=date(2026, 11, 13))
    out_esc = evaluate_patient(p_esc, [MedicationInput(name="Lorazepam", prn=False)])
    f_esc = next(f for f in out_esc.findings if "PHY-CNS-001" in f.rule_ids)
    assert f_esc.severity.value == "urgent"

    # Downgrade with epilepsy (G40) -> consider
    p_dg = Patient(age_years=75, diagnoses=["G40"], review_date=date(2026, 11, 13))
    out_dg = evaluate_patient(p_dg, [MedicationInput(name="Lorazepam", prn=False)])
    f_dg = next(f for f in out_dg.findings if "PHY-CNS-001" in f.rule_ids)
    assert f_dg.severity.value == "consider"


def test_phy_cv_002_digoxin_and_renal_escalation() -> None:
    p = Patient(
        age_years=80, sex=Sex.MALE, serum_creatinine_umol_l=180.0, review_date=date(2026, 11, 13)
    )
    out = evaluate_patient(
        p, [MedicationInput(name="Digoxin", dose=0.25, unit="mg", frequency="daily")]
    )
    f = next(f for f in out.findings if "PHY-CV-002" in f.rule_ids)
    assert f.severity.value == "urgent"
    assert f.renal_note is not None


def test_phy_cns_003_opioid_bzd_urgent() -> None:
    p = Patient(age_years=70, review_date=date(2026, 11, 13))
    out = evaluate_patient(
        p,
        [
            MedicationInput(name="Hydromorphone", dose=2, unit="mg", frequency="bid"),
            MedicationInput(name="Lorazepam", dose=1, unit="mg", frequency="qhs"),
        ],
    )
    f = next(f for f in out.findings if "PHY-CNS-003" in f.rule_ids)
    assert f.severity.value == "urgent"


def test_omissions_separate_in_extended_pack() -> None:
    p = Patient(
        age_years=75,
        diagnoses=["I50"],
        care_setting=CareSetting.COMMUNITY,
        review_date=date(2026, 11, 13),
    )
    out = evaluate_patient(p, [], include_drafts=True)
    assert any(o.rule_id == "PHY-START-002" for o in out.omissions)
    assert all(not f.rule_ids[0].startswith("PHY-START") for f in out.findings)
