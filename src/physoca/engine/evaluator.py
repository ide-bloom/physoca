"""Main rule evaluation orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from physoca.engine.loader import load_packs
from physoca.engine.merge import merge_findings
from physoca.engine.predicates import EvalContext, evaluate_predicate
from physoca.engine.scoring.anticholinergic import compute_anticholinergic_summary
from physoca.engine.scoring.fall_risk import compute_fall_risk_summary
from physoca.engine.trace import make_audit_entry
from physoca.models.finding import (
    AnticholinergicSummary,
    AuditEntry,
    EvidenceInfo,
    FallRiskSummary,
    Finding,
    NeedsDataItem,
    OmissionFinding,
    Severity,
    SourceRef,
    TaperInfo,
)
from physoca.models.medication import MedicationInput, NormalizedMedication
from physoca.models.patient import Patient
from physoca.normalize.diagnoses import normalize_diagnoses
from physoca.normalize.names import normalize_medication
from physoca.normalize.renal import compute_cockcroft_gault, compute_egfr_ckd_epi_2021

_SEV_ORDER = [Severity.CONSIDER, Severity.REVIEW, Severity.URGENT]


@dataclass
class EvaluationOutput:
    medications: list[NormalizedMedication]
    findings: list[Finding]
    omissions: list[OmissionFinding]
    anticholinergic: AnticholinergicSummary
    fall_risk: FallRiskSummary
    needs_data: list[NeedsDataItem]
    audit_trace: list[AuditEntry]
    egfr: float | None
    egfr_source: str | None
    crcl: float | None
    diagnoses: list[str]
    pack_name: str
    pack_version: str


def _shift_severity(sev: Severity, delta: int) -> Severity:
    idx = _SEV_ORDER.index(sev)
    new_idx = max(0, min(len(_SEV_ORDER) - 1, idx + delta))
    return _SEV_ORDER[new_idx]


def _matches_target(med: NormalizedMedication, target: dict[str, Any]) -> bool:
    if not target:
        return False
    exclude_atc = [p.upper() for p in target.get("exclude_atc_prefix", [])]
    if any(atc.upper().startswith(ex) for atc in med.atc_codes for ex in exclude_atc):
        return False

    if "class_group" in target and target["class_group"] in med.class_groups:
        return True
    if "atc_prefix" in target:
        prefixes = [p.upper() for p in target["atc_prefix"]]
        if any(atc.upper().startswith(p) for atc in med.atc_codes for p in prefixes):
            return True
    if "ingredient_any" in target:
        targets = {i.lower() for i in target["ingredient_any"]}
        if med.ingredient.lower() in targets:
            return True
    return False


def _localize_rule(rule: dict[str, Any], lang: str) -> tuple[str, str, str, str | None, str]:
    if lang == "fr":
        fr = rule.get("i18n", {}).get("fr", {})
        return (
            fr.get("title", rule["title"]),
            fr.get("rationale", rule["rationale"]),
            fr.get("action", rule["action"]),
            fr.get("alternatives", rule.get("alternatives")),
            fr.get("taper_note", rule["taper"]["note"]),
        )
    return (
        rule["title"],
        rule["rationale"],
        rule["action"],
        rule.get("alternatives"),
        rule["taper"]["note"],
    )


def _disclaimer(lang: str) -> str:
    if lang == "fr":
        return (
            "Aide à la décision destinée à l'examen par un professionnel de la santé. "
            "Ne constitue pas un diagnostic ni une directive de traitement."
        )
    return (
        "Decision support for review by a health care professional. "
        "Not a diagnosis or treatment direction."
    )


def evaluate_patient(
    patient: Patient,
    medications: list[MedicationInput],
    lang: str = "en",
    include_drafts: bool = False,
) -> EvaluationOutput:
    """Run deterministic rule evaluation on a patient and medication list."""
    norm_dx = normalize_diagnoses(patient.diagnoses)
    norm_meds: list[NormalizedMedication] = []
    for m in medications:
        norm_meds.extend(normalize_medication(m, patient))

    egfr: float | None = patient.egfr_ml_min_1_73
    egfr_source: str | None = "provided" if egfr is not None else None
    if egfr is None and patient.serum_creatinine_umol_l is not None:
        egfr = compute_egfr_ckd_epi_2021(
            patient.serum_creatinine_umol_l, patient.age_years, patient.sex
        )
        if egfr is not None:
            egfr_source = "CKD-EPI 2021"

    crcl: float | None = None
    if patient.serum_creatinine_umol_l is not None:
        crcl = compute_cockcroft_gault(
            patient.serum_creatinine_umol_l, patient.age_years, patient.weight_kg, patient.sex
        )

    ctx = EvalContext(
        patient=patient,
        diagnoses=norm_dx,
        medications=norm_meds,
        egfr=egfr,
        crcl=crcl,
    )

    anticholinergic = compute_anticholinergic_summary(norm_meds, threshold=3, lang=lang)
    fall_risk = compute_fall_risk_summary(patient, norm_meds, lang=lang)

    packs = load_packs(include_drafts=include_drafts)
    pack_name = packs[0]["pack"] if packs else "physoca-core"
    pack_version = packs[0]["pack_version"] if packs else "2026.11.0"

    raw_findings: list[Finding] = []
    omissions: list[OmissionFinding] = []
    needs_data: list[NeedsDataItem] = []
    audit_trace: list[AuditEntry] = []

    for pack in packs:
        for rule in pack.get("rules", []):
            rid = rule["id"]
            rver = int(rule["version"])
            age_min = int(rule.get("population", {}).get("age_min", 0))
            if patient.age_years < age_min:
                audit_trace.append(make_audit_entry(rid, rver, "not_applicable"))
                continue

            title, rationale, action, alternatives, taper_note = _localize_rule(rule, lang)
            sources = [SourceRef(**s) for s in rule.get("sources", [])]
            evidence = EvidenceInfo(**rule["evidence"])
            taper = TaperInfo(
                needed=rule["taper"]["needed"],
                abrupt_stop_risk=rule["taper"]["abrupt_stop_risk"],
                note=taper_note,
            )

            # 1. Omission rules (START-style)
            if rule.get("kind") == "omission":
                when_res = evaluate_predicate(rule.get("when", {}), ctx)
                if when_res.matched is None:
                    audit_trace.append(
                        make_audit_entry(
                            rid, rver, "needs_data", missing_fields=when_res.missing_fields
                        )
                    )
                    needs_data.append(
                        NeedsDataItem(
                            rule_id=rid, title=title, missing_fields=when_res.missing_fields
                        )
                    )
                    continue
                if not when_res.matched:
                    audit_trace.append(make_audit_entry(rid, rver, "not_matched"))
                    continue
                if "exempt_if" in rule:
                    ex_res = evaluate_predicate(rule["exempt_if"], ctx)
                    if ex_res.matched:
                        audit_trace.append(
                            make_audit_entry(
                                rid,
                                rver,
                                "exempted",
                                exemptions_evaluated=ex_res.matched_conditions,
                            )
                        )
                        continue
                audit_trace.append(
                    make_audit_entry(
                        rid, rver, "matched", matched_conditions=when_res.matched_conditions
                    )
                )
                omissions.append(
                    OmissionFinding(
                        rule_id=rid,
                        title=title,
                        category=rule["category"],
                        rationale=rationale,
                        action=action,
                        evidence=evidence,
                        sources=sources,
                    )
                )
                continue

            # 2. Scoring rules (e.g., PHY-ANTICH-002)
            if "scoring" in rule:
                thresh = int(rule["scoring"].get("threshold_gte", 3))
                if (
                    max(
                        anticholinergic.acb_total,
                        anticholinergic.cals_total,
                        anticholinergic.danish_2024_total,
                    )
                    >= thresh
                ):
                    sev = Severity(rule["severity"])
                    matched_conds = [f"acb_total={anticholinergic.acb_total}"]
                    renal_used = None
                    if "escalate_if" in rule:
                        esc = evaluate_predicate(rule["escalate_if"], ctx)
                        if esc.matched:
                            sev = _shift_severity(sev, 1)
                            matched_conds.extend(esc.matched_conditions)
                        if esc.renal_estimate_used:
                            renal_used = esc.renal_estimate_used
                    meds_list = [d.ingredient for d in anticholinergic.contributing_drugs]
                    audit_trace.append(
                        make_audit_entry(
                            rid,
                            rver,
                            "matched",
                            matched_conditions=matched_conds,
                            renal_estimate_used=renal_used,
                        )
                    )
                    raw_findings.append(
                        Finding(
                            rule_ids=[rid],
                            title=title,
                            category=rule["category"],
                            severity=sev,
                            medications=meds_list or ["anticholinergic_regimen"],
                            rationales=[rationale],
                            action=action,
                            alternatives=alternatives,
                            taper=taper,
                            evidence=evidence,
                            sources=sources,
                            renal_note=renal_used,
                            disclaimer=_disclaimer(lang),
                        )
                    )
                else:
                    audit_trace.append(make_audit_entry(rid, rver, "not_matched"))
                continue

            # 3. Set rules (PHY-CNS-002, PHY-CNS-003)
            if "set_rule" in rule:
                sr = rule["set_rule"]
                if "distinct_ingredients_gte" in sr:
                    cg = sr["class_group"]
                    needed_n = int(sr["distinct_ingredients_gte"])
                    matching_ings = sorted(
                        {m.ingredient for m in norm_meds if cg in m.class_groups}
                    )
                    if len(matching_ings) >= needed_n:
                        sev = Severity(rule["severity"])
                        matched_conds = [f"distinct_{cg}={len(matching_ings)}"]
                        if "escalate_if" in rule:
                            esc = evaluate_predicate(rule["escalate_if"], ctx)
                            if esc.matched:
                                sev = _shift_severity(sev, 1)
                                matched_conds.extend(esc.matched_conditions)
                        audit_trace.append(
                            make_audit_entry(rid, rver, "matched", matched_conditions=matched_conds)
                        )
                        raw_findings.append(
                            Finding(
                                rule_ids=[rid],
                                title=title,
                                category=rule["category"],
                                severity=sev,
                                medications=matching_ings,
                                rationales=[rationale],
                                action=action,
                                alternatives=alternatives,
                                taper=taper,
                                evidence=evidence,
                                sources=sources,
                                disclaimer=_disclaimer(lang),
                            )
                        )
                    else:
                        audit_trace.append(make_audit_entry(rid, rver, "not_matched"))
                    continue

                if "pairs" in sr:
                    if "exempt_if" in rule:
                        ex_res = evaluate_predicate(rule["exempt_if"], ctx)
                        if ex_res.matched:
                            audit_trace.append(
                                make_audit_entry(
                                    rid,
                                    rver,
                                    "exempted",
                                    exemptions_evaluated=ex_res.matched_conditions,
                                )
                            )
                            continue
                    pair_matched = False
                    for pair in sr["pairs"]:
                        cg_a = pair["a"]["class_group"]
                        cg_b = pair["b"]["class_group"]
                        meds_a = sorted({m.ingredient for m in norm_meds if cg_a in m.class_groups})
                        meds_b = sorted({m.ingredient for m in norm_meds if cg_b in m.class_groups})
                        if meds_a and meds_b:
                            pair_matched = True
                            sev = Severity(pair.get("severity", rule["severity"]))
                            combined = sorted(set(meds_a + meds_b))
                            audit_trace.append(
                                make_audit_entry(
                                    rid, rver, "matched", matched_conditions=[f"{cg_a}+{cg_b}"]
                                )
                            )
                            raw_findings.append(
                                Finding(
                                    rule_ids=[rid],
                                    title=title,
                                    category=rule["category"],
                                    severity=sev,
                                    medications=combined,
                                    rationales=[rationale],
                                    action=action,
                                    alternatives=alternatives,
                                    taper=taper,
                                    evidence=evidence,
                                    sources=sources,
                                    disclaimer=_disclaimer(lang),
                                )
                            )
                    if not pair_matched:
                        audit_trace.append(make_audit_entry(rid, rver, "not_matched"))
                    continue

            # 4. Per-drug rules
            target = rule.get("target", {})
            matching_meds = [m for m in norm_meds if _matches_target(m, target)]
            if not matching_meds:
                audit_trace.append(make_audit_entry(rid, rver, "not_applicable"))
                continue

            for med in matching_meds:
                ctx.current_drug = med
                when_node = rule.get("when")
                if when_node:
                    when_res = evaluate_predicate(when_node, ctx)
                    if when_res.matched is None:
                        audit_trace.append(
                            make_audit_entry(
                                rid, rver, "needs_data", missing_fields=when_res.missing_fields
                            )
                        )
                        needs_data.append(
                            NeedsDataItem(
                                rule_id=rid,
                                title=title,
                                missing_fields=when_res.missing_fields,
                                medications=[med.ingredient],
                            )
                        )
                        continue
                    if not when_res.matched:
                        audit_trace.append(make_audit_entry(rid, rver, "not_matched"))
                        continue
                    matched_conds = list(when_res.matched_conditions)
                else:
                    matched_conds = ["target_matched"]

                if "exempt_if" in rule:
                    ex_res = evaluate_predicate(rule["exempt_if"], ctx)
                    if ex_res.matched:
                        audit_trace.append(
                            make_audit_entry(
                                rid,
                                rver,
                                "exempted",
                                exemptions_evaluated=ex_res.matched_conditions,
                            )
                        )
                        continue

                sev = Severity(rule["severity"])
                renal_used = None
                if "downgrade_if" in rule:
                    dg = evaluate_predicate(rule["downgrade_if"], ctx)
                    if dg.matched:
                        sev = _shift_severity(sev, -1)
                        matched_conds.extend(dg.matched_conditions)
                if "escalate_if" in rule:
                    esc = evaluate_predicate(rule["escalate_if"], ctx)
                    if esc.matched:
                        sev = _shift_severity(sev, 1)
                        matched_conds.extend(esc.matched_conditions)
                    if esc.renal_estimate_used:
                        renal_used = esc.renal_estimate_used

                med.flags.append(f"{rid}:{sev.value}")
                audit_trace.append(
                    make_audit_entry(
                        rid,
                        rver,
                        "matched",
                        matched_conditions=matched_conds,
                        renal_estimate_used=renal_used,
                    )
                )
                raw_findings.append(
                    Finding(
                        rule_ids=[rid],
                        title=title,
                        category=rule["category"],
                        severity=sev,
                        medications=[med.ingredient],
                        rationales=[rationale],
                        action=action,
                        alternatives=alternatives,
                        taper=taper,
                        evidence=evidence,
                        sources=sources,
                        renal_note=renal_used,
                        disclaimer=_disclaimer(lang),
                    )
                )

    merged_findings = merge_findings(raw_findings)
    return EvaluationOutput(
        medications=norm_meds,
        findings=merged_findings,
        omissions=omissions,
        anticholinergic=anticholinergic,
        fall_risk=fall_risk,
        needs_data=needs_data,
        audit_trace=audit_trace,
        egfr=egfr,
        egfr_source=egfr_source,
        crcl=crcl,
        diagnoses=norm_dx,
        pack_name=pack_name,
        pack_version=pack_version,
    )
