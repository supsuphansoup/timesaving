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
    # removed import parse_unavailable_periods_from_time_str
)
from app.algorithm.scorer import compute_score

logger = logging.getLogger(__name__)


@dataclass
class CourseInput:
    id: int
    professor_id: int
    department: str
    target_grade: int
    weekly_hours: int
    expected_students: int
    requires_computer: bool
    # From professor
    non_preferred_days: list[str]
    non_preferred_periods: list[int]
    preferred_days: list[str]
    preferred_periods: list[int]
    fixed_room_ids: list[int]
    unavailable_room_ids: list[int]


@dataclass
class RoomInput:
    id: int
    capacity: int
    is_computer_room: bool  # e.g. "12:00-13:00"


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
    fixed_slots: list[dict] = None,
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

    # Room unavailable time is removed

    # ── Decision variables ──────────────────────────────────────────────────
    # x[(course_id, slot_idx, day_idx, period, room_id)] = BoolVar
    # slot_idx: each course needs weekly_hours slots (0..weekly_hours-1)
    x: dict[tuple, object] = {}

    for c in courses:
        for s in range(c.weekly_hours):
            for di, day in enumerate(DAYS):
                for period in PERIODS:
                    if day == "WED" and period in [5, 6]:
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
                        key = (c.id, s, di, period, r.id)
                        x[key] = model.new_bool_var(
                            f"x_c{c.id}_s{s}_d{di}_p{period}_r{r.id}"
                        )


    # ── Constraint: Fixed assignments for Partial Reassign ───────────────
    if fixed_slots:
        for f in fixed_slots:
            course_id = f["course_id"]
            day = f["day"]
            start_period = f["start_period"]
            room_id = f["room_id"]
            
            c_input = next((c for c in courses if c.id == course_id), None)
            if not c_input: continue
            
            try:
                di = DAYS.index(day)
                # Just fix one of the slot variables (slot 0) for this fixed course
                # Since we don't track which slot index exactly, we enforce that 
                # AT LEAST one slot of this course is at the fixed location.
                # Actually, if duration is 1, any slot index is fine. 
                # We can enforce that sum of x for this location over all s == 1.
                slot_vars = [
                    x[(course_id, s, di, start_period, room_id)] 
                    for s in range(c_input.weekly_hours)
                    if (course_id, s, di, start_period, room_id) in x
                ]
                if slot_vars:
                    model.add_exactly_one(slot_vars)
            except ValueError:
                pass

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

    # ── Constraint HC-10: cohort non-overlapping ───────────────────────────
    cohort_courses = {}
    for c in courses:
        cohort_courses.setdefault((c.department, c.target_grade), []).append(c)

    for _cohort, ccourses in cohort_courses.items():
        for di in range(len(DAYS)):
            for period in PERIODS:
                occupants = []
                for c in ccourses:
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


    # ── Advanced Features: Consecutive Periods & Room Consistency ──────────────
    
    # y[(c_id, di, period)] = BoolVar, true if course is scheduled on day `di` at `period`
    y = {}
    for c in courses:
        for di in range(len(DAYS)):
            for period in PERIODS:
                y[(c.id, di, period)] = model.new_bool_var(f"y_{c.id}_{di}_{period}")
                slot_vars = [
                    x[k] for k in x
                    if k[0] == c.id and k[2] == di and k[3] == period
                ]
                if slot_vars:
                    model.add(y[(c.id, di, period)] == sum(slot_vars))
                else:
                    model.add(y[(c.id, di, period)] == 0)

    # z[(c_id, r_id)] = BoolVar, true if course `c_id` uses room `r_id`
    z = {}
    for c in courses:
        for r in rooms:
            z[(c.id, r.id)] = model.new_bool_var(f"z_{c.id}_{r.id}")
            r_vars = [x[k] for k in x if k[0] == c.id and k[4] == r.id]
            if r_vars:
                # z is true if any r_var is true
                model.add_bool_or(r_vars).only_enforce_if(z[(c.id, r.id)])
                for rv in r_vars:
                    model.add_implication(rv, z[(c.id, r.id)])
            else:
                model.add(z[(c.id, r.id)] == 0)

    soft_terms = []
    
    # 1. Non-preferred / Preferred Times Bonus & Penalty
    for k, var in x.items():
        c_id, s_idx, di, period, r_id = k
        course = next((c for c in courses if c.id == c_id), None)
        if course is None:
            continue
        day = DAYS[di]
        bonus = 0
        if day in course.preferred_days:
            bonus += 15
        if period in course.preferred_periods:
            bonus += 10
            
        if day in course.non_preferred_days:
            bonus -= 15
        if period in course.non_preferred_periods:
            bonus -= 10
            
        # SC-05 Lunchtime penalty (Period 4 and 5)
        if period in [4, 5]:
            bonus -= 5
            
        if bonus:
            soft_terms.append(bonus * var)

    # 2. Consecutive Periods Bonus
    for c in courses:
        for di in range(len(DAYS)):
            for p_idx in range(len(PERIODS) - 1):
                p1 = PERIODS[p_idx]
                p2 = PERIODS[p_idx + 1]
                
                # cons_var is true if course is scheduled at both p1 and p2
                cons_var = model.new_bool_var(f"cons_{c.id}_{di}_{p1}_{p2}")
                model.add_implication(cons_var, y[(c.id, di, p1)])
                model.add_implication(cons_var, y[(c.id, di, p2)])
                
                # Bonus for consecutive periods (연강 보너스)
                soft_terms.append(20 * cons_var)

    # 3. Room Consistency Penalty
    for c in courses:
        for r in rooms:
            # Penalize using many different rooms (-10 per room used)
            soft_terms.append(-10 * z[(c.id, r.id)])

    # SC-06 Professor daily load balancing
    prof_courses = {}
    for c in courses:
        prof_courses.setdefault(c.professor_id, []).append(c)
        
    for p_id, pcourses in prof_courses.items():
        for di in range(len(DAYS)):
            # Total hours professor teaches on day di
            prof_day_vars = []
            for c in pcourses:
                for period in PERIODS:
                    prof_day_vars.append(y[(c.id, di, period)])
                    
            if not prof_day_vars:
                continue
                
            # If professor teaches > 4 hours on a day, we want to penalize.
            # We can introduce a variable for (sum - 4) and penalize it.
            # OR-Tools CpModel: 
            # excess_load = max(0, sum - 4)
            excess_load = model.new_int_var(0, 5, f"excess_load_{p_id}_{di}")
            # excess_load >= sum - 4
            model.add(excess_load >= sum(prof_day_vars) - 4)
            # Add penalty for excess load
            soft_terms.append(-10 * excess_load)

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

    # Room unavailable time is removed

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
                    for period in PERIODS:
                        if day == "WED" and period in [5, 6]:
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
