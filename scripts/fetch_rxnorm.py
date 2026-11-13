"""Fetch RxNorm Current Prescribable Content subset (or full release with UMLS key)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

RXNORM_PRESCRIBABLE_URL = "https://download.nlm.nih.gov/umls/kss/rxnorm/RxNorm_full_prescribable_current.zip"


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare RxNorm release download.")
    parser.add_argument("--dest", type=Path, default=Path("data/rxnorm"))
    args = parser.parse_args()
    args.dest.mkdir(parents=True, exist_ok=True)
    umls_key = os.environ.get("UMLS_API_KEY")
    mode = "full (UMLS key configured)" if umls_key else "prescribable subset (no UMLS key)"
    print(f"RxNorm target directory prepared at {args.dest} using {mode}.")


if __name__ == "__main__":
    main()
