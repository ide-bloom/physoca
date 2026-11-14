# Data Pipeline

Physoca uses offline-built SQLite reference bundles (`mode=ro`) so runtime execution makes zero outbound network calls.

- **Health Canada DPD**: Open Government Licence - Canada 2.0. Primary ATC and brand-to-ingredient source.
- **RxNorm**: Current Prescribable Content subset (no UMLS key required) or full release with `UMLS_API_KEY`.
- **CCDD & LNHPD**: Optional Canadian terminology and natural health product bridges.

Run `python scripts/build_reference_db.py` or `physoca data build` to rebuild `physoca_ref.db`.
