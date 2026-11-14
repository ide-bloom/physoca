"""Check freshness of DPD, RxNorm, and sources.yaml."""

from __future__ import annotations

import sys
from datetime import date

from physoca.config import Settings
from physoca.engine.loader import load_sources


def main() -> int:
    settings = Settings.from_env()
    sources = load_sources()
    today = date.today()
    warnings: list[str] = []

    dpd_date = date.fromisoformat(settings.dpd_extract_date)
    if (today - dpd_date).days > 35:
        warnings.append(f"DPD extract ({dpd_date}) is older than 35 days.")

    rx_date = date.fromisoformat(settings.rxnorm_release)
    if (today - rx_date).days > 35:
        warnings.append(f"RxNorm release ({rx_date}) is more than one monthly release behind.")

    reviewed = date.fromisoformat(str(sources.get("last_reviewed", today.isoformat())))
    if (today - reviewed).days > 180:
        warnings.append(f"sources.yaml ({reviewed}) has not been reviewed within 180 days.")

    if warnings:
        for w in warnings:
            print(f"WARNING: {w}", file=sys.stderr)
        return 1
    print("Data status OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
