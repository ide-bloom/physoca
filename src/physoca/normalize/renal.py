"""Renal function estimation using CKD-EPI 2021 (race-free) and Cockcroft-Gault."""

from __future__ import annotations

from physoca.models.patient import Sex


def compute_egfr_ckd_epi_2021(
    serum_creatinine_umol_l: float,
    age_years: int,
    sex: Sex,
) -> float | None:
    """Compute race-free CKD-EPI 2021 eGFR in mL/min/1.73m2."""
    if serum_creatinine_umol_l <= 0 or age_years < 18:
        return None
    if sex == Sex.UNSPECIFIED:
        return None

    scr_mg_dl = serum_creatinine_umol_l / 88.4
    if sex == Sex.FEMALE:
        kappa = 0.7
        alpha = -0.241
        sex_factor = 1.012
    else:
        kappa = 0.9
        alpha = -0.302
        sex_factor = 1.0

    ratio = scr_mg_dl / kappa
    egfr = 142.0 * (min(ratio, 1.0) ** alpha) * (max(ratio, 1.0) ** -1.200) * (0.9938**age_years) * sex_factor
    return float(round(egfr, 1))


def compute_cockcroft_gault(
    serum_creatinine_umol_l: float,
    age_years: int,
    weight_kg: float | None,
    sex: Sex,
) -> float | None:
    """Compute Cockcroft-Gault creatinine clearance in mL/min when weight is available."""
    if weight_kg is None or weight_kg <= 0 or serum_creatinine_umol_l <= 0:
        return None
    if sex == Sex.UNSPECIFIED:
        return None

    factor = 1.04 if sex == Sex.FEMALE else 1.23
    crcl = ((140.0 - age_years) * weight_kg * factor) / serum_creatinine_umol_l
    return round(max(crcl, 0.0), 1)
