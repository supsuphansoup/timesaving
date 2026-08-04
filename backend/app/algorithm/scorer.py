"""
Scoring utilities for timetable candidates.

Score = sum of soft-constraint bonuses across all assignments.
Constraint satisfaction rate = satisfied_soft / total_soft (0.0 – 1.0).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.algorithm.engine import CourseInput, SlotAssignment


def compute_score(
    assignments: list["SlotAssignment"],
    courses: list["CourseInput"],
) -> tuple[float, float, int]:
    """
    Returns (score, constraint_satisfaction_rate, conflict_count).

    score  – total soft-constraint bonus points
    csr    – fraction of possible soft-constraint points achieved (0.0-1.0)
    conflict_count – number of hard-constraint violations detected
                     (should be 0 for any valid solver output)
    """
    course_map = {c.id: c for c in courses}

    total_soft = 0
    satisfied_soft = 0
    conflict_count = 0

    # Check conflicts: room double-booking and professor double-booking
    room_slots: dict[tuple, int] = {}   # (day, period, room_id) -> course_id
    prof_slots: dict[tuple, int] = {}   # (day, period, prof_id) -> course_id

    for a in assignments:
        c = course_map.get(a.course_id)
        if c is None:
            continue

        # ── Soft constraint evaluation ──────────────────────────────────────
        # SC-01 preferred day
        total_soft += 1
        if a.day in c.preferred_days:
            satisfied_soft += 1

        # SC-02 preferred period
        total_soft += 1
        if a.start_period in c.preferred_periods:
            satisfied_soft += 1

        # ── Conflict detection ──────────────────────────────────────────────
        room_key = (a.day, a.start_period, a.room_id)
        if room_key in room_slots:
            conflict_count += 1
        else:
            room_slots[room_key] = a.course_id

        prof_key = (a.day, a.start_period, c.professor_id)
        if prof_key in prof_slots:
            conflict_count += 1
        else:
            prof_slots[prof_key] = a.course_id

    csr = satisfied_soft / total_soft if total_soft > 0 else 0.0
    score = float(satisfied_soft * 10)  # 10 points per satisfied soft constraint
    return score, csr, conflict_count
