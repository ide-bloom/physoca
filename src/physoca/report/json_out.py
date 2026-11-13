"""JSON report serializer."""

from __future__ import annotations

from physoca.models.report import ReviewReport


def render_json_report(report: ReviewReport) -> str:
    """Serialize ReviewReport to indented JSON."""
    return report.model_dump_json(indent=2)
