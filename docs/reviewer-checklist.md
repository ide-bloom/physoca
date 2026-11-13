# Pharmacist Reviewer Checklist

Before promoting any rule or releasing a rule pack:

- [ ] Verify every `verified: false` source locator and evidence rating against the primary publication.
- [ ] Confirm `class_groups.yaml` ATC prefixes and ingredient lists.
- [ ] Confirm French (`i18n.fr`) clinical wording for accuracy and clarity.
- [ ] Confirm `a1c_targets.yaml` thresholds against Diabetes Canada Chapter 37.
- [ ] Confirm `evidence.caution: true` is set on any rule derived from a STOPP/START v3 criterion flagged by Boland et al. (2025).
- [ ] Confirm no numeric taper schedules or specific dose recommendations appear in any rule text.
