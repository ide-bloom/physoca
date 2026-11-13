"""Build the read-only SQLite reference database from curated/extracted data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from physoca.config import REFERENCE_DIR
from physoca.normalize.names import _BUILTIN_ATC
from physoca.reference.synonyms import BRAND_TO_INGREDIENTS


def build_db(output_path: Path | None = None) -> Path:
    """Create physoca_ref.db with indexed product, ingredient, and ATC tables."""
    out = output_path or (REFERENCE_DIR / "physoca_ref.db")
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    conn = sqlite3.connect(str(out))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ingredient TEXT NOT NULL,
                atc_code TEXT,
                din TEXT,
                rxcui TEXT,
                source TEXT NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX idx_products_name ON products(lower(name))")
        cur.execute("CREATE INDEX idx_products_din ON products(din)")
        cur.execute("CREATE INDEX idx_products_rxcui ON products(rxcui)")

        for ing, atcs in _BUILTIN_ATC.items():
            for atc in atcs:
                cur.execute(
                    "INSERT INTO products (name, ingredient, atc_code, source) VALUES (?, ?, ?, ?)",
                    (ing, ing, atc, "dpd"),
                )

        for brand, items in BRAND_TO_INGREDIENTS.items():
            for ing, atcs in items:
                for atc in atcs:
                    cur.execute(
                        "INSERT INTO products (name, ingredient, atc_code, source) VALUES (?, ?, ?, ?)",
                        (brand, ing, atc, "dpd"),
                    )

        conn.commit()
    finally:
        conn.close()
    return out


if __name__ == "__main__":
    path = build_db()
    print(f"Built {path}")
