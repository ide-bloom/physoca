"""Rule pack and source registry loader with strict JSON Schema validation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from physoca.config import RULES_DIR
from physoca.reference.classes import load_class_groups


@lru_cache(maxsize=1)
def load_sources() -> dict[str, Any]:
    """Load sources.yaml and return the parsed dictionary."""
    path = RULES_DIR / "sources.yaml"
    with path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return data


def get_sources_ordered() -> list[dict[str, Any]]:
    """Return sources ordered Canadian-first, then international."""
    data = load_sources()
    sources: list[dict[str, Any]] = list(data.get("sources", []))
    ca_jurisdictions = {"CA", "ON", "QC", "BC", "AB"}
    ca = [s for s in sources if s.get("jurisdiction") in ca_jurisdictions]
    intl = [s for s in sources if s.get("jurisdiction") not in ca_jurisdictions]
    return ca + intl


def load_pack(path: Path) -> dict[str, Any]:
    """Load a single YAML rule pack."""
    with path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return data


def load_packs(include_drafts: bool = False) -> list[dict[str, Any]]:
    """Load all rule packs from rules/packs/."""
    packs_dir = RULES_DIR / "packs"
    packs: list[dict[str, Any]] = []
    for path in sorted(packs_dir.glob("*.yaml")):
        pack = load_pack(path)
        if not include_drafts:
            pack = {
                **pack,
                "rules": [r for r in pack.get("rules", []) if r.get("status") == "active"],
            }
        packs.append(pack)
    return packs


def validate_all_rules() -> list[str]:
    """Validate all rule packs against schema.json, sources.yaml, and class_groups.yaml."""
    errors: list[str] = []
    schema_path = RULES_DIR / "schema.json"
    with schema_path.open("r", encoding="utf-8") as fh:
        schema = json.load(fh)

    sources_data = load_sources()
    valid_source_ids = {s["id"] for s in sources_data.get("sources", [])}
    valid_groups = set(load_class_groups().keys())

    packs_dir = RULES_DIR / "packs"
    for path in sorted(packs_dir.glob("*.yaml")):
        pack = load_pack(path)
        try:
            jsonschema.validate(instance=pack, schema=schema)
        except jsonschema.ValidationError as exc:
            errors.append(f"{path.name}: schema error: {exc.message}")
            continue

        for rule in pack.get("rules", []):
            rid = rule.get("id", "<unknown>")
            for src in rule.get("sources", []):
                if src["id"] not in valid_source_ids:
                    errors.append(f"{rid}: unknown source id '{src['id']}'")
            target = rule.get("target", {})
            if "class_group" in target and target["class_group"] not in valid_groups:
                errors.append(f"{rid}: unknown target class_group '{target['class_group']}'")
            if rule.get("status") == "active":
                fr = rule.get("i18n", {}).get("fr", {})
                if not all(fr.get(k) for k in ("title", "rationale", "action")):
                    errors.append(f"{rid}: active rule missing French translation")

    return errors


def check_sources_integrity() -> list[str]:
    """Verify every rule source id exists and every source is used or marked context/legal/data."""
    errors: list[str] = []
    sources_data = load_sources()
    sources = sources_data.get("sources", [])
    source_map = {s["id"]: s for s in sources}

    cited_by_rules: set[str] = set()
    for pack in load_packs(include_drafts=True):
        for rule in pack.get("rules", []):
            for src in rule.get("sources", []):
                sid = src["id"]
                if sid not in source_map:
                    errors.append(f"Rule {rule['id']} cites unknown source '{sid}'")
                else:
                    cited_by_rules.add(sid)

    allowed_uncited_roles = {"context", "legal", "data_source", "patient_resource_link", "scoring_data"}
    for sid, entry in source_map.items():
        if sid not in cited_by_rules and not entry.get("used_by") and entry.get("role") not in allowed_uncited_roles:
            errors.append(f"Source '{sid}' is unused and not marked context")

    return errors
