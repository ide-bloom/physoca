"""Duration calculation in days between start_date and review_date."""

from __future__ import annotations

from datetime import date


def compute_duration_days(start_date: date | None, review_date: date) -> int | None:
    """Return elapsed days from start_date to review_date, or None if start_date is missing."""
    if start_date is None:
        return None
    delta = (review_date - start_date).days
    return max(delta, 0)
