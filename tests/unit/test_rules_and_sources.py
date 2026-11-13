"""Unit tests for rule validation, source registry, safety policy, and exports."""

import html
import json
import re
from pathlib import Path

from physoca.config import (
    DPD_ATTRIBUTION,
    INTENDED_USE_STATEMENT,
    INTENDED_USE_STATEMENT_FR,
    RXNORM_ATTRIBUTION,
)
from physoca.engine.loader import (
    check_sources_integrity,
    get_sources_ordered,
    load_packs,
    validate_all_rules,
)
from physoca.models.medication import MedicationInput
from physoca.models.patient import Patient
from physoca.report.build import build_review_report
from physoca.report.html import render_html_report
from physoca.report.json_out import render_json_report
from physoca.report.pdf import render_pdf_report


def test_rules_and_sources_valid() -> None:
    assert validate_all_rules() == []
    assert check_sources_integrity() == []


def test_canadian_sources_sorted_first() -> None:
    ordered = get_sources_ordered()
    ca_jurisdictions = {"CA", "ON", "QC", "BC", "AB"}
    seen_intl = False
    for s in ordered:
        is_ca = s.get("jurisdiction") in ca_jurisdictions
        if not is_ca:
            seen_intl = True
        elif seen_intl:
            raise AssertionError(f"Canadian source {s['id']} appeared after international source")


def test_no_numeric_taper_schedule_in_rules() -> None:
    taper_pattern = re.compile(r"\b(reduce|taper|decrease)\s+by\s+\d+\s*(%|mg)\b", re.IGNORECASE)
    for pack in load_packs(include_drafts=True):
        for rule in pack.get("rules", []):
            blob = json.dumps(rule, ensure_ascii=False)
            assert not taper_pattern.search(blob), f"Numeric taper schedule found in {rule['id']}"


def test_exports_contain_intended_use_and_attributions() -> None:
    fixture = json.loads(Path("tests/fixtures/patient_polypharmacy.json").read_text(encoding="utf-8"))
    patient = Patient(**fixture["patient"])
    meds = [MedicationInput(**m) for m in fixture["medications"]]

    for lang, expected_use in [("en", INTENDED_USE_STATEMENT), ("fr", INTENDED_USE_STATEMENT_FR)]:
        report = build_review_report(patient, meds, lang=lang)
        j = render_json_report(report)
        h = render_html_report(report)
        p = render_pdf_report(report)
        assert expected_use in j
        assert DPD_ATTRIBUTION in j
        assert RXNORM_ATTRIBUTION in j
        assert expected_use in html.unescape(h)
        assert DPD_ATTRIBUTION in html.unescape(h)
        assert RXNORM_ATTRIBUTION in html.unescape(h)
        assert p.startswith(b"%PDF")
