"""Diagnosis normalization supporting ICD-10-CA prefixes and free-text synonyms."""

from __future__ import annotations

from physoca.reference.synonyms import DIAGNOSIS_SYNONYMS


def normalize_diagnoses(diagnoses: list[str]) -> list[str]:
    """Normalize ICD-10-CA codes and map free-text diagnoses to ICD-10-CA prefixes."""
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in diagnoses:
        cleaned = raw.strip()
        if not cleaned:
            continue
        upper = cleaned.upper()
        # check if it looks like an ICD-10 code (letter followed by digits)
        if len(upper) >= 3 and upper[0].isalpha() and upper[1].isdigit():
            if upper not in seen:
                normalized.append(upper)
                seen.add(upper)
            continue
        lower = cleaned.lower()
        mapped = DIAGNOSIS_SYNONYMS.get(lower)
        if mapped:
            for code in mapped:
                if code not in seen:
                    normalized.append(code)
                    seen.add(code)
        elif upper not in seen:
            normalized.append(upper)
            seen.add(upper)
    return normalized
