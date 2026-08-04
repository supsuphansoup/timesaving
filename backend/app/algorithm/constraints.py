"""
Shared constants and helper functions for the constraint system.
"""

from __future__ import annotations

# ── Time constants ─────────────────────────────────────────────────────────────
DAYS = ["MON", "TUE", "WED", "THU", "FRI"]
PERIODS = list(range(1, 10))  # 1–9

# One period = 1 hour starting at PERIOD_START_HOUR + (period-1)
PERIOD_START_HOUR = 9  # 1st period starts at 09:00


def period_to_hour(period: int) -> int:
    """Convert 1-indexed period to starting hour (24h)."""
    return PERIOD_START_HOUR + (period - 1)


def parse_unavailable_periods_from_time_str(time_str: str | None) -> set[int]:
    """
    Parse a time-range string like "12:00-13:00" or "12:00-13:00,15:00-16:00"
    into a set of unavailable period numbers (1–9).
    """
    if not time_str:
        return set()

    unavailable: set[int] = set()
    for segment in time_str.split(","):
        segment = segment.strip()
        if "-" not in segment:
            continue
        parts = segment.split("-")
        if len(parts) != 2:
            continue
        try:
            start_h = int(parts[0].split(":")[0])
            end_h = int(parts[1].split(":")[0])
        except ValueError:
            continue
        for period in PERIODS:
            p_hour = period_to_hour(period)
            # Mark period unavailable if it falls within the blocked range
            if start_h <= p_hour < end_h:
                unavailable.add(period)
    return unavailable


def build_forbidden_slots(
    unavailable_days: list[str],
    unavailable_periods: list[int],
) -> set[tuple[str, int]]:
    """Return a set of (day, period) tuples that are forbidden."""
    forbidden: set[tuple[str, int]] = set()
    for day in unavailable_days:
        for period in PERIODS:
            forbidden.add((day, period))
    for period in unavailable_periods:
        for day in DAYS:
            forbidden.add((day, period))
    return forbidden
