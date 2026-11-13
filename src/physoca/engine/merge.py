"""Deterministic merging of findings on the same medication."""

from __future__ import annotations

from physoca.models.finding import EvidenceInfo, Finding, SourceRef, TaperInfo

_ABRUPT_RISK_RANK = {"low": 1, "moderate": 2, "high": 3}


def merge_findings(findings: list[Finding]) -> list[Finding]:
    """Merge single-drug findings on the same medication; keep set-based findings separate."""
    by_med: dict[str, list[Finding]] = {}
    set_findings: list[Finding] = []

    for f in findings:
        if len(f.medications) == 1 and not f.rule_ids[0].startswith("PHY-CNS-002"):
            med_key = f.medications[0].lower()
            by_med.setdefault(med_key, []).append(f)
        else:
            set_findings.append(f)

    merged: list[Finding] = []
    for med_key in sorted(by_med.keys()):
        group = sorted(by_med[med_key], key=lambda x: x.rule_ids[0])
        if len(group) == 1:
            merged.append(group[0])
            continue

        highest_sev = max(group, key=lambda x: x.severity.rank()).severity
        rule_ids = sorted({rid for item in group for rid in item.rule_ids})
        rationales = [r for item in group for r in item.rationales]
        seen_src: set[tuple[str, str]] = set()
        sources: list[SourceRef] = []
        for item in group:
            for src in item.sources:
                key = (src.id, src.locator)
                if key not in seen_src:
                    seen_src.add(key)
                    sources.append(src)

        highest_risk_item = max(group, key=lambda x: _ABRUPT_RISK_RANK.get(x.taper.abrupt_stop_risk, 1))
        taper = TaperInfo(
            needed=any(item.taper.needed for item in group),
            abrupt_stop_risk=highest_risk_item.taper.abrupt_stop_risk,
            note=highest_risk_item.taper.note,
        )
        caution = any(item.evidence.caution for item in group)
        evidence = EvidenceInfo(
            quality=group[0].evidence.quality,
            strength=group[0].evidence.strength,
            rating_verified=all(item.evidence.rating_verified for item in group),
            caution=caution,
            note=group[0].evidence.note,
        )
        merged.append(
            Finding(
                rule_ids=rule_ids,
                title=group[0].title,
                category=group[0].category,
                severity=highest_sev,
                medications=group[0].medications,
                rationales=rationales,
                action=" ".join(dict.fromkeys(item.action for item in group)),
                alternatives=next((item.alternatives for item in group if item.alternatives), None),
                taper=taper,
                evidence=evidence,
                sources=sources,
                renal_note=next((item.renal_note for item in group if item.renal_note), None),
                disclaimer=group[0].disclaimer,
            )
        )

    all_findings = merged + set_findings
    return sorted(all_findings, key=lambda f: (-f.severity.rank(), f.category, f.rule_ids[0]))
