"""Audit trace builder for rule evaluation."""

from __future__ import annotations

from physoca.models.finding import AuditEntry


def make_audit_entry(
    rule_id: str,
    rule_version: int,
    outcome: str,
    matched_conditions: list[str] | None = None,
    exemptions_evaluated: list[str] | None = None,
    missing_fields: list[str] | None = None,
    renal_estimate_used: str | None = None,
) -> AuditEntry:
    """Create a structured AuditEntry."""
    return AuditEntry(
        rule_id=rule_id,
        rule_version=rule_version,
        outcome=outcome,
        matched_conditions=matched_conditions or [],
        exemptions_evaluated=exemptions_evaluated or [],
        missing_fields=missing_fields or [],
        renal_estimate_used=renal_estimate_used,
    )
