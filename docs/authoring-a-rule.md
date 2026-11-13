# Authoring a Rule

1. Add the rule to `src/physoca/rules/packs/core.yaml` or `extended.yaml` with `status: draft` until reviewed.
2. Ensure every `source.id` exists in `src/physoca/rules/sources.yaml` and every `class_group` exists in `class_groups.yaml`.
3. Provide `i18n.fr.title`, `i18n.fr.rationale`, and `i18n.fr.action`.
4. Never include a numeric taper schedule or dose reduction percentage.
5. Run `physoca rules validate` and `physoca sources check`.
