"""
Scoring utilities for timetable candidates.

``compute_score`` mirrors the objective function built in ``engine.build_model``
term-for-term, so the score reported to the UI is on the same scale as the value
CP-SAT actually optimized.

pref_rate / fitness_rate = satisfied / total for their respective
soft-constraint groups (0.0 – 1.0).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.algorithm.constraints import (
    BLOCKED_SLOTS,
    LUNCH_PERIODS,
    MAX_DAILY_HOURS_PER_PROFESSOR,
    ONLINE_PERIOD,
)

if TYPE_CHECKING:
    from app.algorithm.engine import CourseInput, RoomInput, SlotAssignment


def compute_score(
    assignments: list["SlotAssignment"],
    courses: list["CourseInput"],
    rooms: list["RoomInput"] | None = None,
) -> tuple[float, float, float, int]:
    """
    Returns (score, pref_rate, fitness_rate, conflict_count).

    score        – same units as the CP-SAT objective (see engine.W_* weights)
    pref_rate    – SC-01/SC-02: fraction of stated 선호 요일/교시 satisfied
    fitness_rate – fraction of other soft constraints satisfied
                   (lunch avoidance, consecutive blocks, professor daily load)

    불가 요일/교시(HC-03/HC-04)는 하드 제약이므로 pref_rate가 아니라
    conflict_count에 집계됩니다 — 수동 편집으로 위반된 경우를 잡아내기 위함입니다.
    """
    # Imported lazily: engine imports this module at load time.
    from app.algorithm.engine import (
        W_CONSECUTIVE,
        W_EXTRA_ROOM,
        W_LUNCH,
        W_PREFERRED_DAY,
        W_PREFERRED_PERIOD,
        W_PROF_IDLE,
        W_PROF_OVERLOAD,
    )

    course_map = {c.id: c for c in courses}
    room_map = {r.id: r for r in (rooms or [])}

    total_pref = 0.0
    satisfied_pref = 0.0
    total_fitness = 0.0
    satisfied_fitness = 0.0
    conflict_count = 0
    engine_score = 0.0

    room_slots: dict[tuple, int] = {}
    prof_slots: dict[tuple, int] = {}
    cohort_slots: dict[tuple, int] = {}
    course_slots: dict[int, list[tuple[str, int]]] = {}
    course_rooms: dict[int, set[int]] = {}

    for a in assignments:
        c = course_map.get(a.course_id)
        if not c:
            continue

        course_slots.setdefault(a.course_id, []).append((a.day, a.start_period))

        # 온라인 수업(0교시)은 강의실이 없다 — 강의실 중복(HC-01)·정원(HC-08)
        # 검사 대상이 아니고, 강의실 이동 감점 계산에도 넣지 않는다.
        is_online = a.room_id is None
        if not is_online:
            course_rooms.setdefault(a.course_id, set()).add(a.room_id)

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

        for cohort in c.target_cohorts or [f"{c.department}_{c.target_grade}"]:
            cohort_key = (a.day, a.start_period, cohort)
            if cohort_key in cohort_slots:
                conflict_count += 1
            else:
                cohort_slots[cohort_key] = a.course_id

        room = room_map.get(a.room_id) if not is_online else None
        if room and room.capacity < c.expected_students:
            conflict_count += 1  # HC-08

        # 0교시는 온라인 전용 — 대면 수업이 놓이면 하드 제약 위반
        if a.start_period == ONLINE_PERIOD and not is_online:
            conflict_count += 1
        if a.start_period != ONLINE_PERIOD and is_online:
            conflict_count += 1

        # HC-03 / HC-04: 불가 요일·교시는 하드 제약이므로 위반 = 충돌
        if a.day in c.non_preferred_days:
            conflict_count += 1
        if a.start_period in c.non_preferred_periods:
            conflict_count += 1

        if (a.day, a.start_period) in BLOCKED_SLOTS:
            conflict_count += 1

        # ── Engine score: day/period preferences + lunch ─────────────────────
        if a.day in c.preferred_days:
            engine_score += W_PREFERRED_DAY
        if a.start_period in c.preferred_periods:
            engine_score += W_PREFERRED_PERIOD
        if a.start_period in LUNCH_PERIODS:
            engine_score += W_LUNCH

        # ── SC-01 / SC-02 preference satisfaction rate (교수 선호도) ──────────
        # Only count if the professor actually specified preferences.
        if c.preferred_days:
            total_pref += 1.0
            if a.day in c.preferred_days:
                satisfied_pref += 1.0

        if c.preferred_periods:
            total_pref += 1.0
            if a.start_period in c.preferred_periods:
                satisfied_pref += 1.0

        # ── Fitness: lunchtime avoidance (always applies) ────────────────────
        total_fitness += 1.0
        if a.start_period not in LUNCH_PERIODS:
            satisfied_fitness += 1.0

    # ── Consecutive periods & room consistency ───────────────────────────────
    for c_id, slots in course_slots.items():
        c = course_map[c_id]

        # Every room beyond the first is penalized (engine: -10 per extra room).
        extra_rooms = max(0, len(course_rooms.get(c_id, set())) - 1)
        engine_score += W_EXTRA_ROOM * extra_rooms

        slots_by_day: dict[str, list[int]] = {}
        for day, period in slots:
            slots_by_day.setdefault(day, []).append(period)

        consecutive_pairs = 0
        for periods in slots_by_day.values():
            periods.sort()
            for i in range(len(periods) - 1):
                if periods[i + 1] == periods[i] + 1:
                    consecutive_pairs += 1

        max_possible = max(0, c.weekly_hours - 1)
        if max_possible > 0:
            total_fitness += max_possible
            satisfied_fitness += min(consecutive_pairs, max_possible)
            # The engine does not reward consecutive slots for "1+1+1" courses.
            if c.block_preference != "1+1+1":
                engine_score += W_CONSECUTIVE * consecutive_pairs

    # ── SC-06 professor daily load & idle time ───────────────────────────────
    prof_day_periods: dict[int, dict[str, list[int]]] = {}
    for a in assignments:
        c = course_map.get(a.course_id)
        if c:
            prof_day_periods.setdefault(c.professor_id, {}).setdefault(a.day, []).append(
                a.start_period
            )

    for day_periods in prof_day_periods.values():
        for periods in day_periods.values():
            count = len(periods)

            total_fitness += 1.0
            if count > MAX_DAILY_HOURS_PER_PROFESSOR:
                engine_score += W_PROF_OVERLOAD * (count - MAX_DAILY_HOURS_PER_PROFESSOR)
            else:
                satisfied_fitness += 1.0

            # Idle ("우주공강"): gaps between the first and last class of the day.
            span = max(periods) - min(periods) + 1
            idle = max(0, span - count)
            total_fitness += 1.0
            if idle:
                engine_score += W_PROF_IDLE * idle
            else:
                satisfied_fitness += 1.0

    pref_rate = satisfied_pref / total_pref if total_pref > 0 else 1.0
    fitness_rate = satisfied_fitness / total_fitness if total_fitness > 0 else 1.0

    return engine_score, pref_rate, fitness_rate, conflict_count
