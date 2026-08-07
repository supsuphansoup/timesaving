"""
Shared constants and helper functions for the constraint system.
"""

from __future__ import annotations

# ── Time constants ─────────────────────────────────────────────────────────────
DAYS = ["MON", "TUE", "WED", "THU", "FRI"]
PERIODS = list(range(0, 10))  # 0교시 – 9교시

# 0교시는 온라인(비대면) 전용이라 강의실을 점유하지 않는다.
# 강의실을 쓰는 대면 수업은 1–9교시에만 배정된다.
ONLINE_PERIOD = 0
ROOM_PERIODS = [p for p in PERIODS if p != ONLINE_PERIOD]

# 한 강의가 가질 수 있는 최대 온라인 시수 (schemas.course.MAX_ONLINE_HOURS와 일치)
MAX_ONLINE_HOURS = 3

# 0교시 starts at 08:00, 1교시 at 09:00, …
PERIOD_START_HOUR = 8

# Slots no course may ever use, e.g. the Wednesday chapel / common hour.
BLOCKED_SLOTS: set[tuple[str, int]] = {("WED", 5), ("WED", 6)}

# Periods that overlap lunch — allowed, but penalized in the objective.
LUNCH_PERIODS: set[int] = {4, 5}

# HC-09: a single course may not run more than this many hours in one day.
MAX_DAILY_HOURS_PER_COURSE = 3

# SC-06: a professor teaching more hours than this in one day is penalized.
MAX_DAILY_HOURS_PER_PROFESSOR = 4


def period_to_hour(period: int) -> int:
    """Convert a period index (0-based, see PERIODS) to its starting hour (24h)."""
    return PERIOD_START_HOUR + period


def parse_unavailable_periods_from_time_str(time_str: str | None) -> set[int]:
    """
    Parse a time-range string like "12:00-13:00" or "12:00-13:00,15:00-16:00"
    into a set of unavailable period numbers.
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
