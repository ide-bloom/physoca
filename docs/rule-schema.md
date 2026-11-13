# Rule Schema

Rule packs are YAML files validated against `src/physoca/rules/schema.json`.

Required fields per rule:
- `id`: `PHY-<DOMAIN>-<NNN>`
- `version`: integer >= 1
- `status`: `active`, `draft`, or `retired`
- `title`, `category`, `severity` (`consider`, `review`, `urgent`)
- `population`: `{age_min: int}`
- `rationale`, `action`, `taper`, `evidence`, `sources`, `i18n.fr`

Allowed predicate namespaces in `when`, `exempt_if`, `downgrade_if`, `escalate_if`:
- `patient`: `age_gte`, `cfs_gte`, `egfr_lt`, `crcl_lt`, `dx_any`, `flag_any`, `setting_any`
- `drug`: `duration_days_gt`, `dose_mg_day_gt`, `indication_any`, `route_any`, `prn`
- `concurrent`: `class_any`, `ingredient_any`, `atc_prefix`
- `lab`: `a1c_lt_individual_target`
- Combinators: `all`, `any`, `not`
