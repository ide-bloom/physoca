"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
RULES_DIR = PACKAGE_DIR / "rules"
REFERENCE_DIR = PACKAGE_DIR / "reference"
I18N_DIR = PACKAGE_DIR / "i18n"
TEMPLATES_DIR = PACKAGE_DIR / "report" / "templates"
STATIC_DIR = PACKAGE_DIR / "report" / "static"

INTENDED_USE_STATEMENT = (
    "Physoca displays and analyzes a patient's medication information against published "
    "prescribing criteria and presents the results, with their sources, to a health care "
    "professional who independently reviews the basis for each result. It does not replace "
    "clinical judgement and is not intended to diagnose, to select a treatment, or to direct "
    "a change in therapy."
)

INTENDED_USE_STATEMENT_FR = (
    "Physoca affiche et analyse les renseignements sur les médicaments d'un patient en "
    "fonction de critères de prescription publiés et présente les résultats, avec leurs "
    "sources, à un professionnel de la santé qui examine de façon indépendante le fondement "
    "de chaque résultat. Il ne remplace pas le jugement clinique et n'est pas destiné à "
    "poser un diagnostic, à choisir un traitement ou à orienter une modification de la thérapie."
)

DPD_ATTRIBUTION = "Contains information licensed under the Open Government Licence - Canada. Health Canada does not provide medical advice."
RXNORM_ATTRIBUTION = "This product uses publicly available data courtesy of the U.S. National Library of Medicine (NLM), National Institutes of Health, Department of Health and Human Services."


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    reference_db_path: Path
    dpd_extract_date: str
    rxnorm_release: str
    max_request_bytes: int
    cors_origins: tuple[str, ...]
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        db_env = os.environ.get("PHYSOCA_DB_PATH")
        db_path = Path(db_env) if db_env else REFERENCE_DIR / "physoca_ref.db"
        cors_raw = os.environ.get("PHYSOCA_CORS_ORIGINS", "").strip()
        cors = tuple(o.strip() for o in cors_raw.split(",") if o.strip()) if cors_raw else ()
        return cls(
            reference_db_path=db_path,
            dpd_extract_date=os.environ.get("PHYSOCA_DPD_DATE", "2026-11-01"),
            rxnorm_release=os.environ.get("PHYSOCA_RXNORM_RELEASE", "2026-11-02"),
            max_request_bytes=int(os.environ.get("PHYSOCA_MAX_REQUEST_BYTES", str(256 * 1024))),
            cors_origins=cors,
            log_level=os.environ.get("PHYSOCA_LOG_LEVEL", "INFO"),
        )
