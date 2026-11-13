"""Class group membership resolution from class_groups.yaml."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from physoca.config import RULES_DIR


@lru_cache(maxsize=1)
def load_class_groups() -> dict[str, dict[str, Any]]:
    """Load class group definitions from rules/class_groups.yaml."""
    path = RULES_DIR / "class_groups.yaml"
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    groups: dict[str, dict[str, Any]] = data.get("groups", {})
    return groups


def get_class_groups_for_drug(
    ingredient: str,
    atc_codes: list[str],
    route: str = "oral",
) -> list[str]:
    """Return sorted list of class group names matching the given drug."""
    groups = load_class_groups()
    ing_lower = ingredient.lower()
    route_lower = route.lower()
    matched: list[str] = []

    for group_name, spec in groups.items():
        routes = [r.lower() for r in spec.get("routes", [])]
        if routes and route_lower not in routes:
            continue

        exclude_atc = [p.upper() for p in spec.get("exclude_atc_prefix", [])]
        if any(atc.upper().startswith(ex) for atc in atc_codes for ex in exclude_atc):
            continue

        exclude_ing = {i.lower() for i in spec.get("exclude_ingredients", [])}
        if ing_lower in exclude_ing:
            continue

        ing_list = {i.lower() for i in spec.get("ingredients", [])}
        atc_prefixes = [p.upper() for p in spec.get("atc_prefix", [])]

        if ing_lower in ing_list or any(
            atc.upper().startswith(p) for atc in atc_codes for p in atc_prefixes
        ):
            matched.append(group_name)

    return sorted(matched)
