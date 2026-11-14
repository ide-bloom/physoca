"""Medication name normalization, salt/strength stripping, and ingredient expansion."""

from __future__ import annotations

import re

from physoca.models.medication import MedicationInput, NormalizedMedication
from physoca.models.patient import Patient
from physoca.normalize.doses import normalize_dose
from physoca.normalize.durations import compute_duration_days
from physoca.reference.classes import get_class_groups_for_drug
from physoca.reference.db import lookup_drug_in_db
from physoca.reference.synonyms import BRAND_TO_INGREDIENTS, INGREDIENT_SYNONYMS

_SALT_PATTERN = re.compile(
    r"\b(hydrochloride|hcl|sodium|maleate|tartrate|fumarate|mesylate|besylate|"
    r"potassium|succinate|citrate|phosphate|sulfate|sulphate|acetate|"
    r"bromide|nitrate|monohydrate|dihydrate|er|xr|sr|cr|dr|ec)\b",
    re.IGNORECASE,
)
_STRENGTH_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|%)(?:/\d+(?:\.\d+)?\s*(?:mg|ml))?\b", re.IGNORECASE
)


def clean_drug_name(raw_name: str) -> str:
    """Strip strengths, salts, and extra whitespace from a drug name."""
    text = raw_name.strip().lower()
    text = _STRENGTH_PATTERN.sub(" ", text)
    text = _SALT_PATTERN.sub(" ", text)
    text = re.sub(r"[,()]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_medication(med: MedicationInput, patient: Patient) -> list[NormalizedMedication]:
    """Normalize a MedicationInput into one or more NormalizedMedication rows."""
    cleaned = clean_drug_name(med.name)
    mg_day, doses_per_day, dose_display = normalize_dose(
        med.dose, med.unit, med.frequency, prn=med.prn
    )
    duration_days = compute_duration_days(med.start_date, patient.review_date)
    route = (med.route or "oral").strip().lower()

    # 1. Try reference SQLite DB if present
    db_matches = lookup_drug_in_db(cleaned, din=med.din, rxcui=med.rxcui)
    if db_matches:
        rows: list[NormalizedMedication] = []
        for match in db_matches:
            ing = INGREDIENT_SYNONYMS.get(match.ingredient.lower(), match.ingredient.lower())
            atcs = match.atc_codes
            groups = get_class_groups_for_drug(ing, atcs, route)
            rows.append(
                NormalizedMedication(
                    original_name=med.name,
                    ingredient=ing,
                    recognized=True,
                    resolution_source=match.source,
                    din=med.din or match.din,
                    rxcui=med.rxcui or match.rxcui,
                    atc_codes=atcs,
                    class_groups=groups,
                    original_dose_display=dose_display,
                    dose_mg_day=mg_day,
                    doses_per_day=doses_per_day,
                    route=route,
                    start_date=med.start_date,
                    duration_days=duration_days,
                    indication=med.indication,
                    prn=med.prn,
                )
            )
        return rows

    # 2. Try curated brand-to-ingredient map (supports multi-ingredient expansion)
    if cleaned in BRAND_TO_INGREDIENTS:
        ingredients = BRAND_TO_INGREDIENTS[cleaned]
        rows = []
        for ing_raw, atcs in ingredients:
            ing = INGREDIENT_SYNONYMS.get(ing_raw.lower(), ing_raw.lower())
            groups = get_class_groups_for_drug(ing, atcs, route)
            rows.append(
                NormalizedMedication(
                    original_name=med.name,
                    ingredient=ing,
                    recognized=True,
                    resolution_source="brand_map",
                    din=med.din,
                    rxcui=med.rxcui,
                    atc_codes=atcs,
                    class_groups=groups,
                    original_dose_display=dose_display,
                    dose_mg_day=mg_day,
                    doses_per_day=doses_per_day,
                    route=route,
                    start_date=med.start_date,
                    duration_days=duration_days,
                    indication=med.indication,
                    prn=med.prn,
                )
            )
        return rows

    # 3. Try direct ingredient synonym or known ATC map
    canonical = INGREDIENT_SYNONYMS.get(cleaned, cleaned)
    # Handle slash-separated combination generics like "tramadol/acetaminophen"
    parts = [p.strip() for p in re.split(r"[/+]", canonical) if p.strip()]
    if len(parts) > 1:
        rows = []
        for part in parts:
            ing = INGREDIENT_SYNONYMS.get(part, part)
            atcs = _BUILTIN_ATC.get(ing, [])
            groups = get_class_groups_for_drug(ing, atcs, route)
            recognized = bool(atcs or groups or ing in _KNOWN_INGREDIENTS)
            rows.append(
                NormalizedMedication(
                    original_name=med.name,
                    ingredient=ing,
                    recognized=recognized,
                    resolution_source="synonym" if recognized else "unrecognized",
                    din=med.din,
                    rxcui=med.rxcui,
                    atc_codes=atcs,
                    class_groups=groups,
                    original_dose_display=dose_display,
                    dose_mg_day=mg_day,
                    doses_per_day=doses_per_day,
                    route=route,
                    start_date=med.start_date,
                    duration_days=duration_days,
                    indication=med.indication,
                    prn=med.prn,
                    flags=[] if recognized else ["unrecognized"],
                )
            )
        return rows

    atcs = _BUILTIN_ATC.get(canonical, [])
    groups = get_class_groups_for_drug(canonical, atcs, route)
    recognized = bool(atcs or groups or canonical in _KNOWN_INGREDIENTS)
    return [
        NormalizedMedication(
            original_name=med.name,
            ingredient=canonical,
            recognized=recognized,
            resolution_source="synonym" if recognized else "unrecognized",
            din=med.din,
            rxcui=med.rxcui,
            atc_codes=atcs,
            class_groups=groups,
            original_dose_display=dose_display,
            dose_mg_day=mg_day,
            doses_per_day=doses_per_day,
            route=route,
            start_date=med.start_date,
            duration_days=duration_days,
            indication=med.indication,
            prn=med.prn,
            flags=[] if recognized else ["unrecognized"],
        )
    ]


_BUILTIN_ATC: dict[str, list[str]] = {
    "omeprazole": ["A02BC01"],
    "pantoprazole": ["A02BC02"],
    "lansoprazole": ["A02BC03"],
    "rabeprazole": ["A02BC04"],
    "esomeprazole": ["A02BC05"],
    "dexlansoprazole": ["A02BC06"],
    "lorazepam": ["N05BA06"],
    "diazepam": ["N05BA01"],
    "oxazepam": ["N05BA04"],
    "alprazolam": ["N05BA12"],
    "clonazepam": ["N03AE01", "N05BA"],
    "temazepam": ["N05CD07"],
    "triazolam": ["N05CD05"],
    "zopiclone": ["N05CF01"],
    "zolpidem": ["N05CF02"],
    "diphenhydramine": ["R06AA02"],
    "hydroxyzine": ["N05BB01"],
    "dimenhydrinate": ["R06AA02"],
    "chlorpheniramine": ["R06AB04"],
    "amitriptyline": ["N06AA09"],
    "nortriptyline": ["N06AA10"],
    "paroxetine": ["N06AB05"],
    "sertraline": ["N06AB06"],
    "citalopram": ["N06AB04"],
    "glyburide": ["A10BB01"],
    "gliclazide": ["A10BB09"],
    "glimepiride": ["A10BB12"],
    "glipizide": ["A10BB07"],
    "metformin": ["A10BA02"],
    "acetylsalicylic acid": ["B01AC06"],
    "ibuprofen": ["M01AE01"],
    "naproxen": ["M01AE02"],
    "diclofenac": ["M01AB05"],
    "meloxicam": ["M01AC06"],
    "celecoxib": ["M01AH01"],
    "prednisone": ["H02AB07"],
    "prednisolone": ["H02AB06"],
    "dexamethasone": ["H02AB02"],
    "warfarin": ["B01AA03"],
    "apixaban": ["B01AF02"],
    "rivaroxaban": ["B01AF01"],
    "dabigatran": ["B01AE07"],
    "risperidone": ["N05AX08"],
    "quetiapine": ["N05AH04"],
    "olanzapine": ["N05AH03"],
    "haloperidol": ["N05AD01"],
    "digoxin": ["C01AA05"],
    "morphine": ["N02AA01"],
    "hydromorphone": ["N02AA03"],
    "oxycodone": ["N02AA05"],
    "fentanyl": ["N02AB03"],
    "tramadol": ["N02AX02"],
    "codeine": ["N02AA59"],
    "gabapentin": ["N03AX12", "N02BF01"],
    "pregabalin": ["N03AX16", "N02BF02"],
    "amlodipine": ["C08CA01"],
    "furosemide": ["C03CA01"],
    "atorvastatin": ["C10AA05"],
    "rosuvastatin": ["C10AA07"],
    "ramipril": ["C09AA05"],
    "acetaminophen": ["N02BE01"],
    "oxybutynin": ["G04BD04"],
    "tolterodine": ["G04BD07"],
    "solifenacin": ["G04BD08"],
    "donepezil": ["N06DA02"],
    "memantine": ["N06DX01"],
    "metoprolol": ["C07AB02"],
}

_KNOWN_INGREDIENTS: set[str] = set(_BUILTIN_ATC.keys()) | {
    "vitamin d",
    "calcium",
    "melatonin",
    "insulin glargine",
    "insulin lispro",
}
