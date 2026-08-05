"""
OR-Tools CP-SAT based timetable generation engine.

Model overview
--------------
* Time axis: Days = {MON, TUE, WED, THU, FRI}  ×  Periods = {1 … 9}
* Each course c needs exactly weekly_hours[c] (day, period, room) slots.
* For simplicity each slot = 1 period.  A course with weekly_hours=3 gets
  3 separate (day, period, room) triples which may be spread across days
  or consecutive – the solver decides.

Hard constraints modelled
--------------------------
HC-01  One course per room-time slot
HC-02  One course per professor-time slot
HC-03  Professor unavailable days → forbidden slots
HC-04  Professor unavailable periods → forbidden slots
HC-05  Fixed room → only allowed rooms for those courses
HC-06  Unavailable rooms for professor → forbidden
HC-07  Requires computer → computer rooms only
HC-08  Room capacity ≥ expected_students
HC-09  Room unavailable_time → forbidden slots (parsed as period list)

Soft constraints (objective)
------------------------------
SC-01  Preferred days → bonus per slot on preferred day
SC-02  Preferred periods → bonus per slot on preferred period

Multiple candidates
-------------------
The solver is called with enumerate_all_solutions via SolutionCallback.
We collect up to min_candidates solutions, each with a distinct assignment.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.algorithm.constraints import (
    DAYS,
    PERIODS,
    build_forbidden_slots,
    parse_unavailable_periods_from_time_str,
)
from app.algorithm.scorer import compute_score

logger = logging.getLogger(__name__)


@dataclass
class CourseInput:
    id: int
    professor_id: int
    weekly_hours: int
    expected_students: int
    requires_computer: bool
    # From professor
    unavailable_days: list[str]
    unavailable_periods: list[int]
    preferred_days: list[str]
    preferred_periods: list[int]
    fixed_room_ids: list[int]
    unavailable_room_ids: list[int]


@dataclass
class RoomInput:
    id: int
    capacity: int
    is_computer_room: bool
    unavailable_time: str | None  # e.g. "12:00-13:00"


@dataclass
class SlotAssignment:
    course_id: int
    room_id: int
    day: str
    start_period: int
    duration: int = 1


@dataclass
class TimetableResult:
    assignments: list[SlotAssignment]
    score: float
    constraint_satisfaction_rate: float
    conflict_count: int


def solve(
    courses: list[CourseInput],
    rooms: list[RoomInput],
    min_candidates: int = 3,
    timeout_seconds: int = 120,
) -> list[TimetableResult]:
    """
    Run the CP-SAT solver and return up to min_candidates timetable solutions.
    Returns an empty list if infeasible.
    """
    try:
        from ortools.sat.python import cp_model  # type: ignore
    except ImportError:
        logger.warning("OR-Tools가 설치되어 있지 않습니다. 폴백 알고리즘을 사용합니다.")
        return _fallback_solve(courses, rooms, min_candidates)

    model = cp_model.CpModel()

    # Pre-compute room unavailable periods from unavailable_time string
    room_unavailable_periods: dict[int, set[int]] = {}
    for r in rooms:
        room_unavailable_periods[r.id] = parse_unavailable_periods_from_time_str(r.unavailable_time)

    # ── Decision variables ──────────────────────────────────────────────────
    # x[(course_id, slot_idx, day_idx, period, room_id)] = BoolVar
    # slot_idx: each course needs weekly_hours slots (0..weekly_hours-1)
    x: dict[tuple, object] = {}

    for c in courses:
        for s in range(c.weekly_hours):
            for di, day in enumerate(DAYS):
                for period in PERIODS:
                    for r in rooms:
                        # Pre-filter obviously forbidden combinations
                        if day in c.unavailable_days:
                            continue
                        if period in c.unavailable_periods:
                            continue
                        if c.fixed_room_ids and r.id not in c.fixed_room_ids:
                            continue
                        if r.id in c.unavailable_room_ids:
                            continue
                        if c.requires_computer and not r.is_computer_room:
                            continue
                        if r.capacity < c.expected_students:
                            continue
                        if period in room_unavailable_periods.get(r.id, set()):
                            continue
                        key = (c.id, s, di, period, r.id)
                        x[key] = model.new_bool_var(
                            f"x_c{c.id}_s{s}_d{di}_p{period}_r{r.id}"
                        )

    # ── Constraint: each slot of each course assigned exactly once ─────────
    for c in courses:
        for s in range(c.weekly_hours):
            slot_vars = [
                x[k]
                for k in x
                if k[0] == c.id and k[1] == s
            ]
            if not slot_vars:
                # No feasible slot → infeasible
                logger.warning(f"강의 ID {c.id}에 대한 가능한 슬롯이 없습니다. 제약조건을 완화하세요.")
                return []
            model.add_exactly_one(slot_vars)

    # ── Constraint HC-01: one course per room-time ─────────────────────────
    for di, day in enumerate(DAYS):
        for period in PERIODS:
            for r in rooms:
                occupants = [
                    x[k]
                    for k in x
                    if k[2] == di and k[3] == period and k[4] == r.id
                ]
                if len(occupants) > 1:
                    model.add_at_most_one(occupants)

    # ── Constraint HC-02: one course per professor-time ────────────────────
    # Group courses by professor
    prof_courses: dict[int, list[CourseInput]] = {}
    for c in courses:
        prof_courses.setdefault(c.professor_id, []).append(c)

    for _prof_id, pcourses in prof_courses.items():
        for di in range(len(DAYS)):
            for period in PERIODS:
                occupants = []
                for c in pcourses:
                    for s in range(c.weekly_hours):
                        for k in x:
                            if (k[0] == c.id and k[1] == s
                                    and k[2] == di and k[3] == period):
                                occupants.append(x[k])
                if len(occupants) > 1:
                    model.add_at_most_one(occupants)

    # ── Constraint HC-09: max 3 hours per day per course ───────────────────
    for c in courses:
        for di in range(len(DAYS)):
            day_vars = [
                x[k]
                for k in x
                if k[0] == c.id and k[2] == di
            ]
            if len(day_vars) > 3:
                model.add_linear_constraint(sum(day_vars), 0, 3)


    # ── Objective: maximise soft constraint satisfaction ───────────────────
    soft_terms = []
    for k, var in x.items():
        c_id, s_idx, di, period, r_id = k
        course = next((c for c in courses if c.id == c_id), None)
        if course is None:
            continue
        day = DAYS[di]
        bonus = 0
        if day in course.preferred_days:
            bonus += 15  # 요일 선호 가중치 상향
        if period in course.preferred_periods:
            bonus += 10
        if bonus:
            soft_terms.append(bonus * var)

    if soft_terms:
        model.maximize(sum(soft_terms))

    # ── Solve and collect multiple solutions ───────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.num_search_workers = 4

    results: list[TimetableResult] = []

    class SolutionCollector(cp_model.CpSolverSolutionCallback):
        def __init__(self, limit: int):
            super().__init__()
            self._limit = limit
            self._count = 0

        def on_solution_callback(self):
            if self._count >= self._limit:
                self.stop_search()
                return
            assignments = []
            for k, var in x.items():
                if self.value(var):
                    c_id, s_idx, di, period, r_id = k
                    assignments.append(
                        SlotAssignment(
                            course_id=c_id,
                            room_id=r_id,
                            day=DAYS[di],
                            start_period=period,
                            duration=1,
                        )
                    )
            score, csr, conflicts = compute_score(assignments, courses)
            results.append(
                TimetableResult(
                    assignments=assignments,
                    score=score,
                    constraint_satisfaction_rate=csr,
                    conflict_count=conflicts,
                )
            )
            self._count += 1

    collector = SolutionCollector(min_candidates)
    status = solver.solve(model, collector)

    if status in (cp_model.INFEASIBLE,):
        logger.warning("OR-Tools: 해를 찾을 수 없습니다 (INFEASIBLE).")
        return []

    # Sort by score descending (best first)
    results.sort(key=lambda r: r.score, reverse=True)
    return results


# ── Fallback solver (when OR-Tools is not available) ──────────────────────────

def _fallback_solve(
    courses: list[CourseInput],
    rooms: list[RoomInput],
    min_candidates: int,
) -> list[TimetableResult]:
    """
    Simple greedy random assignment for environments without OR-Tools.
    Does not guarantee optimality but respects hard constraints.
    """
    import random
    from app.algorithm.scorer import compute_score

    results: list[TimetableResult] = []

    room_unavailable_periods: dict[int, set[int]] = {}
    for r in rooms:
        room_unavailable_periods[r.id] = parse_unavailable_periods_from_time_str(r.unavailable_time)

    for attempt in range(min_candidates * 5):
        if len(results) >= min_candidates:
            break

        assignments: list[SlotAssignment] = []
        # Track occupied (day, period, room) and (day, period, professor)
        room_slots: set[tuple] = set()
        prof_slots: set[tuple] = set()
        success = True

        shuffled_courses = courses.copy()
        random.shuffle(shuffled_courses)

        for c in shuffled_courses:
            for s in range(c.weekly_hours):
                # Build candidate slots
                candidates = []
                for day in DAYS:
                    if day in c.unavailable_days:
                        continue
                    for period in PERIODS:
                        if period in c.unavailable_periods:
                            continue
                        if (day, period, c.professor_id) in prof_slots:
                            continue
                        for r in rooms:
                            if c.fixed_room_ids and r.id not in c.fixed_room_ids:
                                continue
                            if r.id in c.unavailable_room_ids:
                                continue
                            if c.requires_computer and not r.is_computer_room:
                                continue
                            if r.capacity < c.expected_students:
                                continue
                            if period in room_unavailable_periods.get(r.id, set()):
                                continue
                            if (day, period, r.id) in room_slots:
                                continue
                            candidates.append((day, period, r.id))

                if not candidates:
                    success = False
                    break

                day, period, room_id = random.choice(candidates)
                room_slots.add((day, period, room_id))
                prof_slots.add((day, period, c.professor_id))
                assignments.append(
                    SlotAssignment(
                        course_id=c.id,
                        room_id=room_id,
                        day=day,
                        start_period=period,
                        duration=1,
                    )
                )
            if not success:
                break

        if success and assignments:
            score, csr, conflicts = compute_score(assignments, courses)
            results.append(
                TimetableResult(
                    assignments=assignments,
                    score=score,
                    constraint_satisfaction_rate=csr,
                    conflict_count=conflicts,
                )
            )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:min_candidates]
