"""Multi-scale anticholinergic burden scoring (ACB, CALS, Danish 2024)."""

from __future__ import annotations

from functools import lru_cache

import yaml

from physoca.config import RULES_DIR
from physoca.models.finding import AnticholinergicDrugScore, AnticholinergicSummary
from physoca.models.medication import NormalizedMedication


@lru_cache(maxsize=1)
def _load_scale(filename: str) -> dict[str, int]:
    path = RULES_DIR / "scales" / filename
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return {str(k).lower(): int(v) for k, v in data.get("scores", {}).items()}


def compute_anticholinergic_summary(
    medications: list[NormalizedMedication],
    threshold: int = 3,
    lang: str = "en",
) -> AnticholinergicSummary:
    """Compute ACB, CALS, and Danish 2024 totals and flag scale disagreement."""
    acb_map = _load_scale("acb_2012.yaml")
    cals_map = _load_scale("cals_2022.yaml")
    danish_map = _load_scale("danish_2024.yaml")

    seen: set[str] = set()
    drugs: list[AnticholinergicDrugScore] = []
    acb_total = 0
    cals_total = 0
    danish_total = 0

    for med in medications:
        ing = med.ingredient.lower()
        if ing in seen:
            continue
        seen.add(ing)
        s_acb = acb_map.get(ing)
        s_cals = cals_map.get(ing)
        s_dan = danish_map.get(ing)
        if any(s is not None and s > 0 for s in (s_acb, s_cals, s_dan)):
            acb_total += s_acb or 0
            cals_total += s_cals or 0
            danish_total += s_dan or 0
            drugs.append(
                AnticholinergicDrugScore(
                    ingredient=med.ingredient,
                    acb=s_acb,
                    cals=s_cals,
                    danish_2024=s_dan,
                )
            )

    totals = [acb_total, cals_total, danish_total]
    diff_disagree = (max(totals) - min(totals)) >= 2
    threshold_disagree = any(t >= threshold for t in totals) and any(t < threshold for t in totals)
    disagree = diff_disagree or threshold_disagree

    disagreement_note = ""
    if disagree:
        disagreement_note = (
            "Les échelles anticholinergiques divergent pour ce schéma thérapeutique."
            if lang == "fr"
            else "Anticholinergic scales disagree on total burden or threshold crossing."
        )

    citation_note = (
        "Aucune échelle de référence unique n'existe; 74 % des médicaments à forte activité "
        "sont cotés de façon incohérente selon les échelles (J Am Geriatr Soc 2026;74(6):1771-1784)."
        if lang == "fr"
        else "No gold standard anticholinergic scale exists; 74% of high-potency drugs "
        "are scored inconsistently across scales (J Am Geriatr Soc 2026;74(6):1771-1784)."
    )

    return AnticholinergicSummary(
        acb_total=acb_total,
        cals_total=cals_total,
        danish_2024_total=danish_total,
        threshold_gte=threshold,
        scale_disagreement=disagree,
        disagreement_note=disagreement_note,
        contributing_drugs=drugs,
        citation_note=citation_note,
    )
