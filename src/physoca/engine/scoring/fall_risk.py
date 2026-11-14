"""CDC STEADI fall-risk-increasing drug class grouping."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from physoca.config import RULES_DIR
from physoca.models.finding import FallRiskSummary
from physoca.models.medication import NormalizedMedication
from physoca.models.patient import HistoryFlag, Patient


@lru_cache(maxsize=1)
def _load_steadi() -> dict[str, dict[str, Any]]:
    path = RULES_DIR / "scales" / "steadi_fall_risk.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    classes: dict[str, dict[str, Any]] = data.get("classes", {})
    return classes


def compute_fall_risk_summary(
    patient: Patient,
    medications: list[NormalizedMedication],
    lang: str = "en",
) -> FallRiskSummary:
    """List fall-risk-increasing drug classes when falls flag is present or age >= 80."""
    has_falls = HistoryFlag.FALLS in patient.history_flags
    if not (has_falls or patient.age_years >= 80):
        return FallRiskSummary(applicable=False)

    reason = (
        ("Antécédent de chutes consigné" if has_falls else "Âge de 80 ans ou plus")
        if lang == "fr"
        else ("Falls history flag present" if has_falls else "Age 80 years or over")
    )

    steadi = _load_steadi()
    grouped: dict[str, list[str]] = {}
    for _, spec in steadi.items():
        label = spec.get("label_fr" if lang == "fr" else "label_en", "")
        ing_set = {i.lower() for i in spec.get("ingredients", [])}
        matched = sorted({m.ingredient for m in medications if m.ingredient.lower() in ing_set})
        if matched:
            grouped[label] = matched

    return FallRiskSummary(applicable=True, reason=reason, classes=grouped)
