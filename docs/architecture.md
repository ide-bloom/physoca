# Architecture

Physoca is a stateless, deterministic pipeline:

1. **Input validation** (`physoca.models`): Pydantic v2 models validate patient demographics, labs, diagnoses, and medications.
2. **Normalization** (`physoca.normalize`): Strips salts and strengths, resolves brand names to canonical ingredients via DPD/RxNorm/synonyms, expands multi-ingredient products, parses frequencies into mg/day, computes elapsed duration in days, and estimates eGFR (CKD-EPI 2021) and CrCl (Cockcroft-Gault).
3. **Rule evaluation** (`physoca.engine`): Evaluates YAML rule packs validated against `schema.json`. Supports per-drug rules, set rules, multi-scale anticholinergic scoring (ACB, CALS, Danish 2024), CDC STEADI fall-risk grouping, and separate START-style omissions.
4. **Report generation** (`physoca.report`): Produces versioned JSON, accessible WCAG 2.2 AA HTML, and in-memory PDF via WeasyPrint in English and French.
