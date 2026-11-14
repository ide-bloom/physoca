"""Read-only SQLite reference database lookup."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from physoca.config import Settings


@dataclass(frozen=True)
class DrugMatch:
    ingredient: str
    atc_codes: list[str]
    din: str | None = None
    rxcui: str | None = None
    source: str = "dpd"


def lookup_drug_in_db(
    cleaned_name: str,
    din: str | None = None,
    rxcui: str | None = None,
    db_path: Path | None = None,
) -> list[DrugMatch]:
    """Query the read-only SQLite reference bundle if present."""
    path = db_path or Settings.from_env().reference_db_path
    if not path.exists():
        return []

    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.cursor()
        if din:
            cur.execute(
                "SELECT ingredient, atc_code, din, rxcui, source FROM products WHERE din = ?",
                (din,),
            )
            rows = cur.fetchall()
            if rows:
                return _group_rows(rows)
        if rxcui:
            cur.execute(
                "SELECT ingredient, atc_code, din, rxcui, source FROM products WHERE rxcui = ?",
                (rxcui,),
            )
            rows = cur.fetchall()
            if rows:
                return _group_rows(rows)
        cur.execute(
            "SELECT ingredient, atc_code, din, rxcui, source FROM products WHERE lower(name) = ?",
            (cleaned_name.lower(),),
        )
        rows = cur.fetchall()
        return _group_rows(rows)
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _group_rows(rows: list[tuple[str, str | None, str | None, str | None, str]]) -> list[DrugMatch]:
    by_ing: dict[str, DrugMatch] = {}
    for ing, atc, din, rxcui, src in rows:
        key = ing.lower()
        if key not in by_ing:
            by_ing[key] = DrugMatch(
                ingredient=key,
                atc_codes=[atc] if atc else [],
                din=din,
                rxcui=rxcui,
                source=src,
            )
        elif atc and atc not in by_ing[key].atc_codes:
            by_ing[key].atc_codes.append(atc)
    return list(by_ing.values())
