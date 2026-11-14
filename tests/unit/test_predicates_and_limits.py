"""Additional unit tests for predicates, rate limiter, and CLI subcommands."""

from datetime import date

from typer.testing import CliRunner

from physoca.api.limits import LocalRateLimiter
from physoca.cli import app as cli_app
from physoca.engine.predicates import EvalContext, evaluate_predicate
from physoca.models.medication import MedicationInput
from physoca.models.patient import CareSetting, Patient, Sex
from physoca.normalize.names import normalize_medication

runner = CliRunner()


def test_rate_limiter() -> None:
    lim = LocalRateLimiter(max_requests=2, window_seconds=60)
    assert lim.allow("127.0.0.1") is True
    assert lim.allow("127.0.0.1") is True
    assert lim.allow("127.0.0.1") is False


def test_predicates_coverage() -> None:
    p = Patient(
        age_years=75,
        sex=Sex.FEMALE,
        weight_kg=60.0,
        serum_creatinine_umol_l=120.0,
        a1c_percent=6.2,
        individualized_a1c_target_percent=7.5,
        care_setting=CareSetting.LONG_TERM_CARE,
        clinical_frailty_scale=6,
        review_date=date(2026, 11, 13),
    )
    meds = normalize_medication(
        MedicationInput(name="acetylsalicylic acid", dose=81, unit="mg", frequency="daily", indication="secondary prevention"),
        p,
    )
    ctx = EvalContext(patient=p, diagnoses=[], medications=meds, egfr=40.0, crcl=35.0, current_drug=meds[0])

    assert evaluate_predicate({"patient": {"age_gte": 65}}, ctx).matched is True
    assert evaluate_predicate({"patient": {"cfs_gte": 6}}, ctx).matched is True
    assert evaluate_predicate({"patient": {"crcl_lt": 50}}, ctx).matched is True
    assert evaluate_predicate({"patient": {"setting_any": ["long_term_care"]}}, ctx).matched is True
    assert evaluate_predicate({"lab": {"a1c_lt_individual_target": True}}, ctx).matched is True
    assert evaluate_predicate({"drug": {"indication_any": ["secondary prevention"]}}, ctx).matched is True
    assert evaluate_predicate({"not": {"patient": {"age_gte": 90}}}, ctx).matched is True


def test_cli_rules_list_and_show() -> None:
    res_list = runner.invoke(cli_app, ["rules", "list"])
    assert res_list.exit_code == 0
    assert "PHY-GI-001" in res_list.stdout

    res_show = runner.invoke(cli_app, ["rules", "show", "PHY-GI-001"])
    assert res_show.exit_code == 0
    assert "Proton pump inhibitor" in res_show.stdout


def test_merge_findings_same_drug() -> None:
    from physoca.engine.merge import merge_findings
    from physoca.models.finding import EvidenceInfo, Finding, Severity, SourceRef, TaperInfo

    f1 = Finding(
        rule_ids=["PHY-A-001"],
        title="Rule A",
        category="cat",
        severity=Severity.CONSIDER,
        medications=["lorazepam"],
        rationales=["R1"],
        action="A1",
        taper=TaperInfo(needed=False, abrupt_stop_risk="low", note="N1"),
        evidence=EvidenceInfo(),
        sources=[SourceRef(id="ags_beers_2023", locator="loc1", verified=False)],
    )
    f2 = Finding(
        rule_ids=["PHY-B-001"],
        title="Rule B",
        category="cat",
        severity=Severity.URGENT,
        medications=["lorazepam"],
        rationales=["R2"],
        action="A2",
        taper=TaperInfo(needed=True, abrupt_stop_risk="high", note="N2"),
        evidence=EvidenceInfo(caution=True),
        sources=[SourceRef(id="ags_beers_2023", locator="loc2", verified=False)],
    )
    merged = merge_findings([f1, f2])
    assert len(merged) == 1
    assert merged[0].severity == Severity.URGENT
    assert merged[0].rule_ids == ["PHY-A-001", "PHY-B-001"]
    assert merged[0].taper.abrupt_stop_risk == "high"
    assert merged[0].evidence.caution is True
