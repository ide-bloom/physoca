# Physoca

Physoca is a deterministic, rule-based deprescribing decision-support tool for older adults (aged 65 and over by default). It evaluates a structured patient profile and medication list against published prescribing criteria and returns a traceable medication review for a pharmacist, physician, or nurse practitioner.

## Intended use

Physoca displays and analyzes a patient's medication information against published prescribing criteria and presents the results, with their sources, to a health care professional who independently reviews the basis for each result. It does not replace clinical judgement and is not intended to diagnose, to select a treatment, or to direct a change in therapy.

## Why Physoca

The 2026 Canadian primary care guideline on potentially inappropriate prescribing (McDonald et al., *Can Fam Physician* 2026;72(3):173-178) recommends regular prescription checkups for adults 65 and over, pairing medication review with suggestions produced through a structured set of rules. In Canada, Health Canada's *A Prescription for Action* (2025) and the Canadian Drug Agency Transition Office report (2024) highlight inappropriate medication use as a national priority, while CIHI data (2016) documented roughly 1.9 million seniors chronically using at least one potentially inappropriate medication.

Physoca supports that workflow by:
- Running deterministically with no machine-learning, statistical, or generative components.
- Linking every finding to a rule id, rule version, source citation, locator, and condition/exemption audit trail.
- Staying stateless and private by default: no patient data is stored, and no outbound network calls occur at runtime.
- Supporting English and French across the web UI, CLI, API, and exported reports.

## Quick start

### Local installation

```bash
pip install -e .
physoca rules validate
physoca review tests/fixtures/patient_polypharmacy.json --format html --lang en > review.html
```

### Sample CLI output (JSON summary)

```bash
physoca review tests/fixtures/patient_polypharmacy.json --format json
```

Produces a structured JSON report containing:
- `patient_summary` (age, renal estimates, missing fields)
- `medications` (normalized ingredients, daily dose in mg/day, duration, flags)
- `findings` (grouped by severity: `urgent`, `review`, `consider`)
- `anticholinergic` (ACB, CRIDECO CALS, and Danish 2024 scores side by side)
- `fall_risk` (CDC STEADI fall-risk-increasing drug classes)
- `omissions` (separate START-style section, never merged with deprescribing flags)
- `audit_trace` (every rule evaluated, matched conditions, exemptions, and missing data)

### Docker

```bash
docker compose up
```

Then open `http://localhost:8000` in your browser.

## Clinical workflow

Physoca is designed to sit alongside clinician and patient tools such as the Deprescribing.org "5 Tips to Manage Polypharmacy" toolkit and the Canadian Medication Appropriateness and Deprescribing Network (CADeN) EMPOWER brochures. Physoca never recommends a specific dose, never provides a taper schedule, never diagnoses, and never prescribes.

## Evidence caution

Where a rule draws on STOPP/START version 3, Physoca surfaces an evidence caution on criteria flagged in the 2025 appraisal by Boland et al. (*Eur Geriatr Med*, doi 10.1007/s41999-025-01386-7), which found roughly one third of cited references to be low-level evidence and ten STOPP criteria without a valid supporting reference. Rules are never hidden; the caution is shown directly on the finding.

## Data sources and licences

- **Health Canada Drug Product Database (DPD)**: Contains information licensed under the Open Government Licence - Canada. Health Canada does not provide medical advice.
- **RxNorm (US National Library of Medicine)**: Uses the Current Prescribable Content subset by default under NLM Terms of Service.
- **Licensed Natural Health Products Database (LNHPD)** and **CCDD**: Optional terminology bridges.

## Limitations and regulatory note

Physoca is decision-support software for review by a health care professional. It does not perform e-prescribing, EMR integration, document parsing, or general drug-drug interaction checking beyond the published rule families in its rule packs. See `docs/regulatory.md` for a summary of Health Canada's Software as a Medical Device (SaMD) guidance and `docs/privacy.md` for Canadian privacy considerations. Neither document constitutes legal advice.
