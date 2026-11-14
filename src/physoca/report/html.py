"""Accessible HTML report renderer."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from physoca.config import I18N_DIR, TEMPLATES_DIR
from physoca.models.report import ReviewReport


@lru_cache(maxsize=2)
def load_i18n(lang: str) -> dict[str, str]:
    """Load UI translation strings for en or fr."""
    code = "fr" if lang == "fr" else "en"
    path = I18N_DIR / f"{code}.json"
    with path.open("r", encoding="utf-8") as fh:
        data: dict[str, str] = json.load(fh)
    return data


def get_jinja_env() -> Environment:
    """Return configured Jinja2 Environment with autoescape enabled."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_html_report(report: ReviewReport) -> str:
    """Render ReviewReport as an accessible WCAG 2.2 AA HTML document."""
    env = get_jinja_env()
    template = env.get_template("report.html")
    t: dict[str, Any] = load_i18n(report.language)
    return template.render(report=report, t=t)
