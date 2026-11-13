# Contributing to Physoca

1. Fork the repository and create a feature branch.
2. Install development dependencies: `pip install -e ".[dev]"`.
3. Run `ruff check .`, `mypy src`, `physoca rules validate`, and `pytest` before opening a pull request.
4. Any new rule must include `i18n.fr` translations, at least one valid `sources.yaml` entry, and positive, negative, exemption, and escalation/downgrade test fixtures.
5. Never include numeric taper schedules or real patient data in rules, tests, or fixtures.
