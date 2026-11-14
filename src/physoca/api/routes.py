"""API and server-rendered web UI routes."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from physoca.config import INTENDED_USE_STATEMENT, INTENDED_USE_STATEMENT_FR, Settings
from physoca.engine.loader import get_sources_ordered, load_packs
from physoca.models.medication import MedicationInput
from physoca.models.patient import Patient
from physoca.report.build import build_review_report
from physoca.report.html import get_jinja_env, load_i18n, render_html_report
from physoca.version import __version__

logger = logging.getLogger("physoca.api")

router = APIRouter()

_SAMPLE_JSON = json.dumps(
    {
        "patient": {
            "age_years": 78,
            "sex": "female",
            "serum_creatinine_umol_l": 95,
            "history_flags": ["falls"],
            "diagnoses": ["I10"],
        },
        "medications": [
            {
                "name": "Pantoprazole",
                "dose": 40,
                "unit": "mg",
                "frequency": "daily",
                "start_date": "2026-01-10",
            },
            {
                "name": "Lorazepam",
                "dose": 1,
                "unit": "mg",
                "frequency": "qhs",
                "start_date": "2026-02-01",
            },
        ],
    },
    indent=2,
)


class ReviewRequest(BaseModel):
    patient: Patient
    medications: list[MedicationInput]
    lang: str = "en"
    include_drafts: bool = False


@router.get("/api/health")
def api_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/version")
def api_version() -> dict[str, str]:
    settings = Settings.from_env()
    packs = load_packs()
    pack_version = packs[0]["pack_version"] if packs else "unknown"
    return {
        "physoca_version": __version__,
        "pack_version": pack_version,
        "dpd_extract_date": settings.dpd_extract_date,
        "rxnorm_release": settings.rxnorm_release,
    }


@router.get("/api/sources")
def api_sources() -> list[dict[str, Any]]:
    return get_sources_ordered()


@router.get("/api/rules")
def api_rules(include_drafts: bool = False) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for pack in load_packs(include_drafts=include_drafts):
        rules.extend(pack.get("rules", []))
    return rules


@router.get("/api/rules/{rule_id}")
def api_rule_detail(rule_id: str) -> dict[str, Any]:
    for pack in load_packs(include_drafts=True):
        for rule in pack.get("rules", []):
            if rule["id"] == rule_id:
                result: dict[str, Any] = rule
                return result
    raise HTTPException(status_code=404, detail="Rule not found")


@router.post("/api/review")
def api_review(payload: ReviewRequest) -> JSONResponse:
    report = build_review_report(
        payload.patient,
        payload.medications,
        lang=payload.lang,
        include_drafts=payload.include_drafts,
    )
    # log only counts and rule ids, never patient or medication data
    logger.info(
        "review_completed findings=%d omissions=%d rules=%s",
        len(report.findings),
        len(report.omissions),
        [rid for f in report.findings for rid in f.rule_ids],
    )
    return JSONResponse(
        content=json.loads(report.model_dump_json()),
        headers={"Cache-Control": "no-store"},
    )


@router.get("/", response_class=HTMLResponse)
def web_index(request: Request, lang: str = Query(default="en")) -> HTMLResponse:
    env = get_jinja_env()
    t = load_i18n(lang)
    intended_use = INTENDED_USE_STATEMENT_FR if lang == "fr" else INTENDED_USE_STATEMENT
    html = env.get_template("index.html").render(
        lang=lang, t=t, sample_json=_SAMPLE_JSON, intended_use=intended_use
    )
    return HTMLResponse(content=html)


@router.post("/review", response_class=HTMLResponse)
def web_review(patient_json: str = Form(...), lang: str = Form(default="en")) -> HTMLResponse:
    try:
        raw = json.loads(patient_json)
        req = ReviewRequest(
            patient=Patient(**raw["patient"]),
            medications=[MedicationInput(**m) for m in raw.get("medications", [])],
            lang=lang,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid input: {exc}") from exc

    report = build_review_report(req.patient, req.medications, lang=lang)
    html = render_html_report(report)
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


@router.get("/references", response_class=HTMLResponse)
def web_references(lang: str = Query(default="en")) -> HTMLResponse:
    env = get_jinja_env()
    t = load_i18n(lang)
    sources = get_sources_ordered()
    html = env.get_template("references.html").render(lang=lang, t=t, sources=sources)
    return HTMLResponse(content=html)
