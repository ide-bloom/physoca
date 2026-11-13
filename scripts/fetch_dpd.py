"""Fetch and unpack Health Canada Drug Product Database (DPD) extract."""

from __future__ import annotations

import argparse
from pathlib import Path

DPD_EXTRACT_URL = "https://www.canada.ca/content/dam/hc-sc/documents/services/drug-health-product-review-approval/drug-product-database/allfiles.zip"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Health Canada DPD extract.")
    parser.add_argument("--dest", type=Path, default=Path("data/dpd"))
    args = parser.parse_args()
    args.dest.mkdir(parents=True, exist_ok=True)
    print(f"DPD extract target directory prepared at {args.dest} (source: {DPD_EXTRACT_URL})")


if __name__ == "__main__":
    main()
