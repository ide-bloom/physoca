# Privacy

Physoca is stateless by design:
- No patient data is written to any database or temporary file (PDFs are rendered in memory).
- Request bodies and medication names are never logged; only rule IDs and counts are logged.
- No cookies, analytics, or third-party network calls are used.

## Canadian Privacy Regimes

Deployers must determine which Canadian privacy statute applies to their setting (this summary is not legal advice):
- **Ontario PHIPA** (`phipa_on`): applies to health information custodians (physicians, hospitals, pharmacies, long-term-care homes).
- **Federal PIPEDA** (`pipeda`): applies to private-sector organizations in provinces without substantially similar legislation, including breach reporting for real risk of significant harm.
- **Quebec Law 25** (`qc_law25`) and **Quebec Law 5** (`qc_law5`, in force July 2024): require privacy impact assessments for certain systems and cross-border communication, breach reporting, and French-language availability—which is why Physoca's UI and reports are fully bilingual.
- **BC and Alberta PIPA** (`bc_ab_pipa`): deployers must also confirm province-specific health information statutes in their jurisdiction.
