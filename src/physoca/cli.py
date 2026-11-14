"""Command-line interface for Physoca."""

from __future__ import annotations

import os
import sys

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")  # noqa: SIM115
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")  # noqa: SIM115

import json
import sys
import threading
import time
import webbrowser
from pathlib import Path

import typer
import uvicorn

from physoca.config import Settings
from physoca.engine.loader import (
    check_sources_integrity,
    load_packs,
    load_sources,
    validate_all_rules,
)
from physoca.models.medication import MedicationInput
from physoca.models.patient import Patient
from physoca.report.build import build_review_report
from physoca.report.html import render_html_report
from physoca.report.json_out import render_json_report
from physoca.report.pdf import render_pdf_report

app = typer.Typer(help="Physoca deterministic deprescribing decision-support CLI.")
rules_app = typer.Typer(help="Inspect and validate rule packs.")
data_app = typer.Typer(help="Inspect and build reference data.")
sources_app = typer.Typer(help="Check reference source registry.")

app.add_typer(rules_app, name="rules")
app.add_typer(data_app, name="data")
app.add_typer(sources_app, name="sources")


@app.command()
def review(
    patient_file: Path = typer.Argument(..., exists=True, readable=True),
    format: str = typer.Option("json", "--format", help="Output format: json, html, pdf"),
    lang: str = typer.Option("en", "--lang", help="Language: en or fr"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Optional output file path"),
    include_drafts: bool = typer.Option(False, "--include-drafts", help="Include draft rules"),
) -> None:
    """Run a medication review on a patient JSON file."""
    raw = json.loads(patient_file.read_text(encoding="utf-8"))
    patient = Patient(**raw["patient"])
    meds = [MedicationInput(**m) for m in raw.get("medications", [])]
    report = build_review_report(patient, meds, lang=lang, include_drafts=include_drafts)

    fmt = format.lower()
    if fmt == "json":
        content = render_json_report(report)
        if output:
            output.write_text(content, encoding="utf-8")
        else:
            typer.echo(content)
    elif fmt == "html":
        content = render_html_report(report)
        if output:
            output.write_text(content, encoding="utf-8")
        else:
            typer.echo(content)
    elif fmt == "pdf":
        pdf_bytes = render_pdf_report(report)
        if output:
            output.write_bytes(pdf_bytes)
        else:
            sys.stdout.buffer.write(pdf_bytes)
    else:
        typer.echo(f"Unsupported format: {format}", err=True)
        raise typer.Exit(code=1)


@rules_app.command("list")
def rules_list(include_drafts: bool = typer.Option(False, "--include-drafts")) -> None:
    """List rules in loaded packs."""
    for pack in load_packs(include_drafts=include_drafts):
        for r in pack.get("rules", []):
            typer.echo(f"{r['id']}\t{r['status']}\t{r['severity']}\t{r['title']}")


@rules_app.command("show")
def rules_show(rule_id: str) -> None:
    """Show full details for a single rule."""
    for pack in load_packs(include_drafts=True):
        for r in pack.get("rules", []):
            if r["id"] == rule_id:
                typer.echo(json.dumps(r, indent=2, ensure_ascii=False))
                return
    typer.echo(f"Rule not found: {rule_id}", err=True)
    raise typer.Exit(code=1)


@rules_app.command("validate")
def rules_validate() -> None:
    """Validate all rule packs against schema.json, sources.yaml, and class_groups.yaml."""
    errors = validate_all_rules()
    if errors:
        for err in errors:
            typer.echo(f"ERROR: {err}", err=True)
        raise typer.Exit(code=1)
    typer.echo("All rule packs validated with zero errors.")


@sources_app.command("check")
def sources_check() -> None:
    """Check source registry integrity."""
    errors = check_sources_integrity()
    if errors:
        for err in errors:
            typer.echo(f"ERROR: {err}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Source registry check passed.")


@data_app.command("status")
def data_status() -> None:
    """Print loaded data versions and warn on stale extracts."""
    settings = Settings.from_env()
    sources = load_sources()
    packs = load_packs()
    pack_ver = packs[0]["pack_version"] if packs else "unknown"
    typer.echo(f"DPD extract date: {settings.dpd_extract_date}")
    typer.echo(f"RxNorm release:   {settings.rxnorm_release}")
    typer.echo(f"Rule pack:        {pack_ver}")
    typer.echo(
        f"Source registry:  {sources.get('registry_version')} (reviewed {sources.get('last_reviewed')})"
    )


@data_app.command("build")
def data_build() -> None:
    """Build the SQLite reference database from local extracts."""
    from scripts.build_reference_db import build_db

    out = build_db()
    typer.echo(f"Built reference database at {out}")


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """Launch the Physoca desktop window when invoked with no subcommand."""
    if ctx.invoked_subcommand is None:
        from physoca.api.app import app as fastapi_app

        port = 8765

        def _run_server() -> None:
            uvicorn.run(fastapi_app, host="127.0.0.1", port=port, log_level="warning")

        threading.Thread(target=_run_server, daemon=True).start()
        time.sleep(1.0)
        try:
            import webview  # type: ignore[import-not-found]

            webview.create_window(
                "Physoca — Deprescribing Decision Support",
                f"http://127.0.0.1:{port}",
                width=1240,
                height=860,
                min_size=(900, 650),
            )
            webview.start()
        except ImportError:
            webbrowser.open(f"http://127.0.0.1:{port}")
            while True:
                time.sleep(1)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port"),
    open_browser: bool = typer.Option(False, "--open/--no-open"),
) -> None:
    """Start the Physoca web UI and API server."""
    from physoca.api.app import app as fastapi_app

    if open_browser:

        def _open() -> None:
            time.sleep(1.0)
            webbrowser.open(f"http://127.0.0.1:{port}")

        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(fastapi_app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
