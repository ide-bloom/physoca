"""Dose and frequency normalization to canonical mg/day."""

from __future__ import annotations

import re

_FREQ_MAP: dict[str, float] = {
    "od": 1.0,
    "qd": 1.0,
    "daily": 1.0,
    "once daily": 1.0,
    "once a day": 1.0,
    "q24h": 1.0,
    "qhs": 1.0,
    "hs": 1.0,
    "at bedtime": 1.0,
    "qam": 1.0,
    "bid": 2.0,
    "twice daily": 2.0,
    "twice a day": 2.0,
    "q12h": 2.0,
    "tid": 3.0,
    "three times daily": 3.0,
    "q8h": 3.0,
    "qid": 4.0,
    "four times daily": 4.0,
    "q6h": 4.0,
    "q4h": 6.0,
    "weekly": 1.0 / 7.0,
    "once weekly": 1.0 / 7.0,
    "qweek": 1.0 / 7.0,
}

_UNIT_TO_MG: dict[str, float] = {
    "mg": 1.0,
    "milligram": 1.0,
    "milligrams": 1.0,
    "g": 1000.0,
    "gram": 1000.0,
    "grams": 1000.0,
    "mcg": 0.001,
    "ug": 0.001,
    "microgram": 0.001,
    "micrograms": 0.001,
}


def parse_frequency(frequency: str | None, prn: bool = False) -> float | None:
    """Parse a medication frequency string into doses per day."""
    if not frequency:
        return None if prn else 1.0
    cleaned = re.sub(r"\s+", " ", frequency.strip().lower())
    cleaned = cleaned.replace("prn", "").strip()
    if not cleaned:
        return None if prn else 1.0
    if cleaned in _FREQ_MAP:
        return _FREQ_MAP[cleaned]
    match = re.match(r"q(\d+)h", cleaned)
    if match:
        hours = int(match.group(1))
        if hours > 0:
            return round(24.0 / hours, 4)
    return None


def normalize_dose(
    dose: float | None,
    unit: str | None,
    frequency: str | None,
    prn: bool = False,
) -> tuple[float | None, float | None, str]:
    """Return (dose_mg_day, doses_per_day, original_display)."""
    doses_per_day = parse_frequency(frequency, prn=prn)
    display_parts = []
    if dose is not None:
        display_parts.append(f"{dose:g}")
    if unit:
        display_parts.append(unit)
    if frequency:
        display_parts.append(frequency)
    display = " ".join(display_parts).strip()

    if dose is None or unit is None or doses_per_day is None:
        return None, doses_per_day, display

    unit_key = unit.strip().lower()
    factor = _UNIT_TO_MG.get(unit_key)
    if factor is None:
        return None, doses_per_day, display

    mg_day = round(dose * factor * doses_per_day, 4)
    return mg_day, doses_per_day, display
