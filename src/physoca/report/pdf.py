"""In-memory PDF report renderer using WeasyPrint."""

from __future__ import annotations

from physoca.models.report import ReviewReport
from physoca.report.html import render_html_report


def render_pdf_report(report: ReviewReport) -> bytes:
    """Render ReviewReport to PDF bytes in memory without writing temp files."""
    try:
        import weasyprint
    except OSError as exc:
        raise RuntimeError(
            "PDF export requires WeasyPrint's GTK/Pango runtime libraries. "
            "Use --format html or --format json, or install GTK3 on Windows."
        ) from exc

    html_str = render_html_report(report)
    pdf_bytes: bytes = weasyprint.HTML(string=html_str).write_pdf()
    return pdf_bytes
