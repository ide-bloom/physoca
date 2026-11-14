"""Predicate evaluator for rule conditions, exemptions, and escalations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from physoca.models.medication import NormalizedMedication
from physoca.models.patient import Patient


@dataclass
class EvalContext:
    patient: Patient
    diagnoses: list[str]
    medications: list[NormalizedMedication]
    egfr: float | None
    crcl: float | None
    current_drug: NormalizedMedication | None = None


@dataclass
class PredicateResult:
    matched: bool | None  # None means needs_data
    missing_fields: list[str] = field(default_factory=list)
    matched_conditions: list[str] = field(default_factory=list)
    renal_estimate_used: str | None = None


def evaluate_predicate(node: dict[str, Any], ctx: EvalContext) -> PredicateResult:
    """Recursively evaluate a predicate AST node."""
    if "all" in node:
        conditions: list[str] = []
        renal_used: str | None = None
        for child in node["all"] or []:
            res = evaluate_predicate(child, ctx)
            if res.renal_estimate_used:
                renal_used = res.renal_estimate_used
            if res.matched is None:
                return PredicateResult(None, res.missing_fields, conditions, renal_used)
            if not res.matched:
                return PredicateResult(False, [], conditions, renal_used)
            conditions.extend(res.matched_conditions)
        return PredicateResult(True, [], conditions, renal_used)

    if "any" in node:
        missing: list[str] = []
        renal_used = None
        for child in node["any"] or []:
            res = evaluate_predicate(child, ctx)
            if res.renal_estimate_used:
                renal_used = res.renal_estimate_used
            if res.matched is True:
                return PredicateResult(True, [], res.matched_conditions, renal_used)
            if res.matched is None:
                missing.extend(res.missing_fields)
        if missing:
            return PredicateResult(None, sorted(set(missing)), [], renal_used)
        return PredicateResult(False, [], [], renal_used)

    if "not" in node:
        res = evaluate_predicate(node["not"], ctx)
        if res.matched is None:
            return res
        return PredicateResult(not res.matched, [], [], res.renal_estimate_used)

    if "patient" in node:
        return _eval_patient(node["patient"], ctx)
    if "drug" in node:
        return _eval_drug(node["drug"], ctx)
    if "concurrent" in node:
        return _eval_concurrent(node["concurrent"], ctx)
    if "lab" in node:
        return _eval_lab(node["lab"], ctx)

    return PredicateResult(False)


def _eval_patient(spec: dict[str, Any], ctx: EvalContext) -> PredicateResult:
    p = ctx.patient
    if "age_gte" in spec:
        ok = p.age_years >= int(spec["age_gte"])
        return PredicateResult(ok, matched_conditions=[f"age>={spec['age_gte']}"] if ok else [])
    if "cfs_gte" in spec:
        if p.clinical_frailty_scale is None:
            return PredicateResult(None, missing_fields=["clinical_frailty_scale"])
        ok = p.clinical_frailty_scale >= int(spec["cfs_gte"])
        return PredicateResult(ok, matched_conditions=[f"cfs>={spec['cfs_gte']}"] if ok else [])
    if "egfr_lt" in spec:
        if ctx.egfr is None:
            return PredicateResult(None, missing_fields=["egfr_ml_min_1_73"])
        ok = ctx.egfr < float(spec["egfr_lt"])
        return PredicateResult(
            ok,
            matched_conditions=[f"egfr<{spec['egfr_lt']}"] if ok else [],
            renal_estimate_used=f"eGFR (CKD-EPI 2021): {ctx.egfr} mL/min/1.73m2",
        )
    if "crcl_lt" in spec:
        if ctx.crcl is None:
            return PredicateResult(None, missing_fields=["weight_kg", "serum_creatinine_umol_l"])
        ok = ctx.crcl < float(spec["crcl_lt"])
        return PredicateResult(
            ok,
            matched_conditions=[f"crcl<{spec['crcl_lt']}"] if ok else [],
            renal_estimate_used=f"CrCl (Cockcroft-Gault): {ctx.crcl} mL/min",
        )
    if "dx_any" in spec:
        prefixes = [str(x).upper() for x in spec["dx_any"]]
        matched = [dx for dx in ctx.diagnoses if any(dx.startswith(pref) for pref in prefixes)]
        return PredicateResult(bool(matched), matched_conditions=[f"dx:{m}" for m in matched])
    if "flag_any" in spec:
        flags = {f.value for f in p.history_flags}
        targets = set(spec["flag_any"])
        hit = sorted(flags & targets)
        return PredicateResult(bool(hit), matched_conditions=[f"flag:{h}" for h in hit])
    if "setting_any" in spec:
        ok = p.care_setting.value in spec["setting_any"]
        return PredicateResult(
            ok, matched_conditions=[f"setting:{p.care_setting.value}"] if ok else []
        )
    return PredicateResult(False)


def _eval_drug(spec: dict[str, Any], ctx: EvalContext) -> PredicateResult:
    d = ctx.current_drug
    if d is None:
        return PredicateResult(False)
    if "duration_days_gt" in spec:
        if d.duration_days is None:
            return PredicateResult(None, missing_fields=["start_date"])
        ok = d.duration_days > int(spec["duration_days_gt"])
        return PredicateResult(
            ok, matched_conditions=[f"duration_days>{spec['duration_days_gt']}"] if ok else []
        )
    if "dose_mg_day_gt" in spec:
        if d.dose_mg_day is None:
            return PredicateResult(None, missing_fields=["dose", "unit", "frequency"])
        ok = d.dose_mg_day > float(spec["dose_mg_day_gt"])
        return PredicateResult(
            ok, matched_conditions=[f"dose_mg_day>{spec['dose_mg_day_gt']}"] if ok else []
        )
    if "indication_any" in spec:
        if not d.indication:
            return PredicateResult(False)
        ind_lower = d.indication.lower()
        ok = any(term.lower() in ind_lower for term in spec["indication_any"])
        return PredicateResult(ok, matched_conditions=[f"indication:{d.indication}"] if ok else [])
    if "route_any" in spec:
        ok = d.route.lower() in [r.lower() for r in spec["route_any"]]
        return PredicateResult(ok, matched_conditions=[f"route:{d.route}"] if ok else [])
    if "prn" in spec:
        ok = d.prn is bool(spec["prn"])
        return PredicateResult(ok, matched_conditions=[f"prn:{d.prn}"] if ok else [])
    return PredicateResult(False)


def _eval_concurrent(spec: dict[str, Any], ctx: EvalContext) -> PredicateResult:
    if "class_any" in spec:
        targets = set(spec["class_any"])
        hits = [m.ingredient for m in ctx.medications if targets & set(m.class_groups)]
        return PredicateResult(
            bool(hits), matched_conditions=[f"concurrent_class:{h}" for h in hits]
        )
    if "ingredient_any" in spec:
        targets = {i.lower() for i in spec["ingredient_any"]}
        hits = [m.ingredient for m in ctx.medications if m.ingredient.lower() in targets]
        return PredicateResult(bool(hits), matched_conditions=[f"concurrent_ing:{h}" for h in hits])
    if "atc_prefix" in spec:
        prefixes = [p.upper() for p in spec["atc_prefix"]]
        hits = [
            m.ingredient
            for m in ctx.medications
            if any(atc.upper().startswith(p) for atc in m.atc_codes for p in prefixes)
        ]
        return PredicateResult(bool(hits), matched_conditions=[f"concurrent_atc:{h}" for h in hits])
    return PredicateResult(False)


def _eval_lab(spec: dict[str, Any], ctx: EvalContext) -> PredicateResult:
    p = ctx.patient
    if spec.get("a1c_lt_individual_target"):
        if p.a1c_percent is None:
            return PredicateResult(None, missing_fields=["a1c_percent"])
        if p.individualized_a1c_target_percent is None:
            return PredicateResult(None, missing_fields=["individualized_a1c_target_percent"])
        ok = p.a1c_percent < p.individualized_a1c_target_percent
        return PredicateResult(
            ok,
            matched_conditions=[
                f"a1c({p.a1c_percent})<target({p.individualized_a1c_target_percent})"
            ]
            if ok
            else [],
        )
    return PredicateResult(False)
