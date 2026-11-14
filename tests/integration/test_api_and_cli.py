"""Integration tests for FastAPI endpoints and Typer CLI."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from physoca.api.app import create_app
from physoca.cli import app as cli_app

client = TestClient(create_app())
runner = CliRunner()


def test_api_endpoints() -> None:
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/version").status_code == 200
    assert client.get("/api/rules").status_code == 200
    assert client.get("/api/rules/PHY-GI-001").status_code == 200
    assert client.get("/api/rules/NONEXISTENT").status_code == 404

    sources_resp = client.get("/api/sources")
    assert sources_resp.status_code == 200
    assert sources_resp.json()[0]["jurisdiction"] in {"CA", "ON", "QC", "BC", "AB"}

    fixture = json.loads(Path("tests/fixtures/patient_polypharmacy.json").read_text(encoding="utf-8"))
    rev = client.post("/api/review", json=fixture)
    assert rev.status_code == 200
    assert rev.headers.get("cache-control") == "no-store"
    assert len(rev.json()["findings"]) >= 1

    assert client.get("/").status_code == 200
    assert client.get("/references").status_code == 200


def test_cli_commands(tmp_path: Path) -> None:
    assert runner.invoke(cli_app, ["rules", "validate"]).exit_code == 0
    assert runner.invoke(cli_app, ["sources", "check"]).exit_code == 0
    assert runner.invoke(cli_app, ["data", "status"]).exit_code == 0

    pdf_out = tmp_path / "review_fr.pdf"
    res = runner.invoke(
        cli_app,
        [
            "review",
            "tests/fixtures/patient_polypharmacy.json",
            "--format",
            "pdf",
            "--lang",
            "fr",
            "--output",
            str(pdf_out),
        ],
    )
    assert res.exit_code == 0
    assert pdf_out.exists() and pdf_out.read_bytes().startswith(b"%PDF")
