"""Validate all Physoca rule packs and source registry."""

from __future__ import annotations

import sys

from physoca.engine.loader import check_sources_integrity, validate_all_rules


def main() -> int:
    errors = validate_all_rules() + check_sources_integrity()
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print("All rules and sources validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
