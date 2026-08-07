"""
OR-Tools CP-SAT based timetable generation engine (2-Phase Architecture).

Phase 1: Find optimal score (Maximize).
Phase 2: Enumerate diverse solutions near the optimal score by adding
         "no-good" diversity cuts to the *same* model (the model is built once).
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass

from app.algorithm.constraints import (
    BLOCKED_SLOTS,
    DAYS,
    LUNCH_PERIODS,
    MAX_DAILY_HOURS_PER_COURSE,
    MAX_DAILY_HOURS_PER_PROFESSOR,
    ONLINE_PERIOD,
    PERIODS,
    ROOM_PERIODS,
)
from app.algorithm.scorer import compute_score

logger = logging.getLogger(__name__)

# ── Soft-constraint weights ───────────────────────────────────────────────────
W_PREFERRED_DAY = 15
W_PREFERRED_PERIOD = 10
W_LUNCH = -5
W_CONSECUTIVE = 20
W_EXTRA_ROOM = -10
W_PROF_OVERLOAD = -10
W_PROF_IDLE = -5

# How many times Phase 2 may re-solve while hunting for diverse candidates.
MAX_PHASE2_ATTEMPTS = 6


class InfeasibleModelError(Exception):
    """Raised when the model cannot be built at all (a course has no legal slot)."""


class SolverTimeoutError(Exception):
    """
    Raised when the solver ran out of time without finding *any* solution.

    This is emphatically NOT the same as "no valid timetable exists" — a
    solution may well exist and simply need a longer budget. Reporting these
    two cases with the same message misleads the user into rewriting perfectly
    good constraints.
    """


@dataclass
class CourseInput:
    id: int
    course_name: str
    professor_id: int
    department: str
    target_grade: int
    weekly_hours: int
    expected_students: int
    requires_computer: bool
    non_preferred_days: list[str]
    non_preferred_periods: list[int]
    preferred_days: list[str]
    preferred_periods: list[int]
    fixed_room_ids: list[int]
    unavailable_room_ids: list[int]
    # 온라인(비대면) 시수 — 0교시에만, 강의실 없이 배정된다.
    online_hours: int = 0
    block_preference: str | None = None
    mutually_exclusive_with: list[str] | None = None
    fixed_schedules: list[dict] | None = None
    target_cohorts: list[str] | None = None


@dataclass
class RoomInput:
    id: int
    capacity: int
    is_computer_room: bool


@dataclass
class SlotAssignment:
    course_id: int
    # 온라인 수업(0교시)은 강의실이 없어 None이다.
    room_id: int | None
    day: str
    start_period: int
    duration: int = 1


@dataclass
class TimetableResult:
    assignments: list[SlotAssignment]
    score: float
    pref_rate: float
    fitness_rate: float
    conflict_count: int


def _slot_is_blocked(day: str, period: int) -> bool:
    return (day, period) in BLOCKED_SLOTS


def build_model(
    courses: list[CourseInput],
    rooms: list[RoomInput],
    fixed_slots: list[dict] = None,
):
    """
    Build the CP-SAT model.

    Returns (model, x, y, obj_var). ``obj_var`` is *not* yet maximized — the
    caller decides between Phase 1 (maximize) and Phase 2 (satisfy + cuts).

    Raises InfeasibleModelError if a course has no legal (day, period, room)
    combination at all, so the caller can report a precise reason.
    """
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()

    course_map = {c.id: c for c in courses}
    room_map = {r.id: r for r in rooms}
    p_min, p_max = min(PERIODS), max(PERIODS)
    n_periods = len(PERIODS)

    x: dict[tuple[int, int, int, int], object] = {}
    y: dict[tuple[int, int, int], object] = {}

    # ── Indexes (avoid O(len(x)) dict scans inside nested loops) ──────────────
    x_by_course: dict[int, list] = defaultdict(list)
    x_by_course_slot: dict[tuple[int, int, int], list] = defaultdict(list)
    x_by_slot_room: dict[tuple[int, int, int], list] = defaultdict(list)
    x_by_course_room: dict[tuple[int, int], list] = defaultdict(list)
    # Number of distinct (day, period) slots a course may legally occupy.
    slot_count_by_course: dict[int, int] = defaultdict(int)

    for c in courses:
        for di in range(len(DAYS)):
            for period in PERIODS:
                y[(c.id, di, period)] = model.new_bool_var(f"y_{c.id}_{di}_{period}")

    # ── Decision variables + HC-05/06/07/08 filtering at creation time ────────
    # ONLINE_PERIOD(0교시)는 비대면 전용이라 강의실을 점유하지 않는다. 따라서 이
    # 교시에는 x(강의실 포함) 변수를 만들지 않고 y(점유)만 사용한다.
    no_room_courses: list[CourseInput] = []
    for c in courses:
        room_hours = c.weekly_hours - c.online_hours

        legal_rooms = []
        for r in rooms:
            if c.fixed_room_ids and r.id not in c.fixed_room_ids:
                continue  # HC-05 fixed room
            if r.id in c.unavailable_room_ids:
                continue  # HC-06 unavailable room
            if c.requires_computer and not r.is_computer_room:
                continue  # HC-07 computer room
            if r.capacity < c.expected_students:
                continue  # HC-08 capacity (hard, matches validate_move/ER-03)
            legal_rooms.append(r)

        if not legal_rooms and room_hours > 0:
            no_room_courses.append(c)
            continue

        for di, day in enumerate(DAYS):
            if day in c.non_preferred_days:
                continue  # HC-03 불가 요일
            for period in ROOM_PERIODS:
                if period in c.non_preferred_periods:
                    continue  # HC-04 불가 교시
                if _slot_is_blocked(day, period):
                    continue
                slot_count_by_course[c.id] += 1
                for r in legal_rooms:
                    key = (c.id, di, period, r.id)
                    var = model.new_bool_var(f"x_c{c.id}_d{di}_p{period}_r{r.id}")
                    x[key] = var
                    x_by_course[c.id].append(var)
                    x_by_course_slot[(c.id, di, period)].append(var)
                    x_by_slot_room[(di, period, r.id)].append(var)
                    x_by_course_room[(c.id, r.id)].append(var)

    if no_room_courses:
        names = ", ".join(f"{c.course_name}(id={c.id})" for c in no_room_courses[:5])
        raise InfeasibleModelError(
            f"배정 가능한 강의실이 없는 강의가 {len(no_room_courses)}개 있습니다: {names}"
            " — 수용 인원/컴퓨터실/고정 강의실 조건을 확인하세요."
        )

    empty_courses = [
        c for c in courses
        if not x_by_course[c.id] and c.weekly_hours - c.online_hours > 0
    ]
    if empty_courses:
        names = ", ".join(f"{c.course_name}(id={c.id})" for c in empty_courses[:5])
        raise InfeasibleModelError(
            f"배정 가능한 시간대가 없는 강의가 {len(empty_courses)}개 있습니다: {names}"
            " — 불가 요일/불가 교시 설정이 너무 넓지 않은지 확인하세요."
        )

    for c in courses:
        room_hours = c.weekly_hours - c.online_hours
        if room_hours > slot_count_by_course[c.id]:
            raise InfeasibleModelError(
                f"'{c.course_name}'(id={c.id})의 대면 시수({room_hours}시간)를 채울 만큼"
                f" 배정 가능한 시간대({slot_count_by_course[c.id]}개)가 없습니다"
                " — 불가 요일/교시 설정을 확인하세요."
            )
        # 온라인 수업은 0교시에만, 하루 1시간씩만 열 수 있다.
        online_days = [
            d for d in DAYS
            if d not in c.non_preferred_days and not _slot_is_blocked(d, ONLINE_PERIOD)
        ]
        if c.online_hours > len(online_days):
            raise InfeasibleModelError(
                f"'{c.course_name}'(id={c.id})의 온라인 시수({c.online_hours}시간)를 배정할"
                f" 0교시 요일이 부족합니다(가능 {len(online_days)}일)"
                " — 불가 요일 설정을 확인하세요."
            )

    # ── Pinned slots (partial reassign) ───────────────────────────────────────
    if fixed_slots:
        for f in fixed_slots:
            course_id, day = f["course_id"], f["day"]
            start_period, room_id = f["start_period"], f["room_id"]
            if course_id not in course_map or day not in DAYS:
                continue
            di = DAYS.index(day)
            key = (course_id, di, start_period, room_id)
            if key in x:
                model.add(x[key] == 1)
            else:
                logger.warning(
                    "고정 요청 슬롯이 제약상 불가능하여 무시합니다: "
                    f"course={course_id} {day} {start_period}교시 room={room_id}"
                )

    # ── Weekly hours: 대면 시수는 x, 온라인 시수는 0교시 y가 담당 ──────────────
    for c in courses:
        model.add(sum(x_by_course[c.id]) == c.weekly_hours - c.online_hours)

        online_vars = [
            y[(c.id, di, ONLINE_PERIOD)]
            for di, day in enumerate(DAYS)
            if day not in c.non_preferred_days and not _slot_is_blocked(day, ONLINE_PERIOD)
        ]
        model.add(sum(online_vars) == c.online_hours)
        # 나머지 0교시 요일(불가 요일 등)은 열 수 없다.
        for di, day in enumerate(DAYS):
            if y[(c.id, di, ONLINE_PERIOD)] not in online_vars:
                model.add(y[(c.id, di, ONLINE_PERIOD)] == 0)

    # ── Link x and y (0교시는 위에서 이미 처리했으므로 제외) ────────────────────
    for c in courses:
        for di in range(len(DAYS)):
            for period in ROOM_PERIODS:
                slot_vars = x_by_course_slot.get((c.id, di, period))
                if slot_vars:
                    model.add_at_most_one(slot_vars)
                    model.add(y[(c.id, di, period)] == sum(slot_vars))
                else:
                    model.add(y[(c.id, di, period)] == 0)

    # ── HC-01 room conflict ───────────────────────────────────────────────────
    for occupants in x_by_slot_room.values():
        if len(occupants) > 1:
            model.add_at_most_one(occupants)

    # ── HC-02 professor conflict ──────────────────────────────────────────────
    prof_courses: dict[int, list[CourseInput]] = defaultdict(list)
    for c in courses:
        prof_courses[c.professor_id].append(c)

    for pcourses in prof_courses.values():
        if len(pcourses) < 2:
            continue
        for di in range(len(DAYS)):
            for period in PERIODS:
                model.add_at_most_one([y[(c.id, di, period)] for c in pcourses])

    # ── HC-10 cohort (same student group) conflict ────────────────────────────
    cohort_courses: dict[str, list[CourseInput]] = defaultdict(list)
    for c in courses:
        for cohort in c.target_cohorts or [f"{c.department}_{c.target_grade}"]:
            cohort_courses[cohort].append(c)

    for ccourses in cohort_courses.values():
        if len(ccourses) < 2:
            continue
        for di in range(len(DAYS)):
            for period in PERIODS:
                model.add_at_most_one([y[(c.id, di, period)] for c in ccourses])

    # ── HC-09 max hours per day, per course ───────────────────────────────────
    for c in courses:
        for di in range(len(DAYS)):
            model.add(
                sum(y[(c.id, di, period)] for period in PERIODS)
                <= MAX_DAILY_HOURS_PER_COURSE
            )

    # ── HC-11 block preference ────────────────────────────────────────────────
    # 연강 블록은 대면 수업(1–9교시)에만 적용한다. 0교시 온라인 수업은 하루 1시간
    # 단발이라 블록 계산에 넣으면 대면 연강 한도를 잘못 깎아먹는다.
    for c in courses:
        block_starts = []
        for di in range(len(DAYS)):
            for p_idx, period in enumerate(ROOM_PERIODS):
                is_start = model.new_bool_var(f"is_start_{c.id}_{di}_{period}")
                if p_idx == 0:
                    model.add(is_start == y[(c.id, di, period)])
                else:
                    prev = ROOM_PERIODS[p_idx - 1]
                    model.add(is_start <= y[(c.id, di, period)])
                    model.add(is_start <= 1 - y[(c.id, di, prev)])
                    model.add(is_start >= y[(c.id, di, period)] - y[(c.id, di, prev)])
                block_starts.append(is_start)

        max_blocks = _max_blocks_for(c)
        if max_blocks is not None:
            model.add(sum(block_starts) <= max_blocks)

    # ── HC-12 mutually exclusive ──────────────────────────────────────────────
    for c in courses:
        exclusive = c.mutually_exclusive_with
        if not exclusive:
            continue
        targets = [
            tc for tc in courses
            if tc.id != c.id
            and tc.course_name
            and any(sub in tc.course_name for sub in exclusive)
        ]
        if not targets:
            continue
        for di in range(len(DAYS)):
            for period in PERIODS:
                model.add_at_most_one(
                    [y[(c.id, di, period)]] + [y[(tc.id, di, period)] for tc in targets]
                )

    # ── HC-13 fixed schedules ─────────────────────────────────────────────────
    for c in courses:
        for fixed in c.fixed_schedules or []:
            day_str, period = fixed.get("day"), fixed.get("period")
            if day_str not in DAYS or period not in PERIODS:
                continue
            if _slot_is_blocked(day_str, period):
                logger.warning(
                    f"강의 {c.id}의 고정 스케줄({day_str} {period}교시)이 "
                    "사용 불가 시간대라 무시합니다."
                )
                continue
            # 0교시는 온라인 전용이라 온라인 시수가 없는 강의는 고정할 수 없다.
            # (그대로 두면 아무 설명 없이 INFEASIBLE로 끝난다)
            if period == ONLINE_PERIOD and not c.online_hours:
                logger.warning(
                    f"강의 {c.id}의 고정 스케줄({day_str} 0교시)은 온라인 전용 시간이지만 "
                    "해당 강의의 온라인 시수가 0이라 무시합니다."
                )
                continue
            if period != ONLINE_PERIOD and c.online_hours >= c.weekly_hours:
                logger.warning(
                    f"강의 {c.id}는 전 시수가 온라인이라 고정 스케줄"
                    f"({day_str} {period}교시)을 무시합니다."
                )
                continue
            model.add(y[(c.id, DAYS.index(day_str), period)] == 1)

    # ── SOFT CONSTRAINTS ──────────────────────────────────────────────────────
    # Track the objective's true range so obj_var's domain can never clip it.
    soft_terms: list = []
    obj_lb = 0
    obj_ub = 0

    def add_soft(coeff: int, var, v_min: int = 0, v_max: int = 1) -> None:
        nonlocal obj_lb, obj_ub
        soft_terms.append(coeff * var)
        lo, hi = sorted((coeff * v_min, coeff * v_max))
        obj_lb += lo
        obj_ub += hi

    def add_const(value: int) -> None:
        nonlocal obj_lb, obj_ub
        if value:
            soft_terms.append(value)
            obj_lb += value
            obj_ub += value

    # 1. SC-01/SC-02 day & period preferences, plus lunch avoidance.
    # (불가 요일/교시 are hard — those variables were never created.)
    for c in courses:
        for di, day in enumerate(DAYS):
            bonus = W_PREFERRED_DAY if day in c.preferred_days else 0
            for period in PERIODS:
                slot_bonus = bonus
                if period in c.preferred_periods:
                    slot_bonus += W_PREFERRED_PERIOD
                if period in LUNCH_PERIODS:
                    slot_bonus += W_LUNCH
                if slot_bonus:
                    add_soft(slot_bonus, y[(c.id, di, period)])

    # 2. Consecutive blocks
    for c in courses:
        if c.block_preference == "1+1+1":
            continue  # this course explicitly wants classes spread out
        for di in range(len(DAYS)):
            for p_idx in range(len(PERIODS) - 1):
                p1, p2 = PERIODS[p_idx], PERIODS[p_idx + 1]
                cons_var = model.new_bool_var(f"cons_{c.id}_{di}_{p1}_{p2}")
                # cons_var == 1 requires both periods occupied (one constraint,
                # not two implications).
                model.add(2 * cons_var <= y[(c.id, di, p1)] + y[(c.id, di, p2)])
                add_soft(W_CONSECUTIVE, cons_var)

    # 3. Room consistency — penalize every room *beyond the first*
    for c in courses:
        used_rooms = []
        for r in rooms:
            r_vars = x_by_course_room.get((c.id, r.id))
            if not r_vars:
                continue
            z = model.new_bool_var(f"z_{c.id}_{r.id}")
            # One aggregated constraint instead of one implication per slot.
            # Equivalent here: z is penalized, so the solver pushes it to 0
            # unless some slot forces it to 1.
            #   (per-slot implications made this the dominant constraint class —
            #    ~397k enforced BoolOr on a 320-course instance, 25s of presolve)
            model.add(sum(r_vars) <= c.weekly_hours * z)
            used_rooms.append(z)
            add_soft(W_EXTRA_ROOM, z)
        # A course always occupies at least one room, so give back one room's
        # worth of penalty. This keeps engine score == scorer score.
        if used_rooms:
            add_const(-W_EXTRA_ROOM)

    # 4. Professor daily load balancing + idle ("우주공강") time
    for p_id, pcourses in prof_courses.items():
        for di in range(len(DAYS)):
            prof_day_vars = [y[(c.id, di, period)] for c in pcourses for period in PERIODS]
            if not prof_day_vars:
                continue

            total_classes = sum(prof_day_vars)

            # Load balancing: hours beyond MAX_DAILY_HOURS_PER_PROFESSOR
            excess = model.new_int_var(0, n_periods, f"excess_{p_id}_{di}")
            model.add(excess >= total_classes - MAX_DAILY_HOURS_PER_PROFESSOR)
            add_soft(W_PROF_OVERLOAD, excess, 0, n_periods)

            # Idle time: (last period - first period + 1) - classes taught
            has_class = model.new_bool_var(f"has_class_{p_id}_{di}")
            model.add(total_classes > 0).only_enforce_if(has_class)
            model.add(total_classes == 0).only_enforce_if(has_class.Not())

            min_p = model.new_int_var(p_min, p_max, f"min_p_{p_id}_{di}")
            max_p = model.new_int_var(p_min, p_max, f"max_p_{p_id}_{di}")

            for p in PERIODS:
                period_vars = [y[(c.id, di, p)] for c in pcourses]
                active = model.new_bool_var(f"active_{p_id}_{di}_{p}")
                model.add_bool_or(period_vars).only_enforce_if(active)
                model.add_bool_and([v.Not() for v in period_vars]).only_enforce_if(active.Not())
                model.add(min_p <= p).only_enforce_if(active)
                model.add(max_p >= p).only_enforce_if(active)

            model.add(min_p == p_min).only_enforce_if(has_class.Not())
            model.add(max_p == p_min).only_enforce_if(has_class.Not())

            # span may legitimately reach len(PERIODS) (first period → last period)
            span = model.new_int_var(0, n_periods, f"span_{p_id}_{di}")
            model.add(span == max_p - min_p + 1).only_enforce_if(has_class)
            model.add(span == 0).only_enforce_if(has_class.Not())

            idle = model.new_int_var(0, n_periods, f"idle_{p_id}_{di}")
            model.add(idle == span - total_classes).only_enforce_if(has_class)
            model.add(idle == 0).only_enforce_if(has_class.Not())

            add_soft(W_PROF_IDLE, idle, 0, n_periods)

    obj_var = model.new_int_var(obj_lb, obj_ub, "objective")
    model.add(obj_var == sum(soft_terms))

    logger.info(
        f"모델 생성 완료: 강의 {len(courses)}개, 강의실 {len(rooms)}개, "
        f"변수 {len(x)}개, 목적함수 범위 [{obj_lb}, {obj_ub}]"
    )
    return model, x, y, obj_var


def _max_blocks_for(c: CourseInput) -> int | None:
    """
    Upper bound on the number of separate consecutive blocks for a course.

    Counted over the *대면* hours only — online hours sit at 0교시 outside the
    block structure entirely.
    """
    pref = c.block_preference
    if pref == "1+1+1":
        return 3
    if pref == "3":
        return 1
    if pref and "+" in pref:
        return len(pref.split("+"))
    room_hours = c.weekly_hours - c.online_hours
    if room_hours <= 2:
        return 1
    if room_hours == 3:
        return 2
    return 2


def _extract_assignments(solver, x, y=None, courses=None) -> list[SlotAssignment]:
    """
    Extract assignments from a solved model.

    Online sessions live only in ``y`` (0교시, no room), so they must be read
    separately or they would silently vanish from the result.
    """
    out = [
        SlotAssignment(
            course_id=c_id, room_id=r_id, day=DAYS[di], start_period=period, duration=1
        )
        for (c_id, di, period, r_id), var in x.items()
        if solver.value(var)
    ]

    if y is not None and courses:
        for c in courses:
            if not c.online_hours:
                continue
            for di in range(len(DAYS)):
                var = y.get((c.id, di, ONLINE_PERIOD))
                if var is not None and solver.value(var):
                    out.append(
                        SlotAssignment(
                            course_id=c.id, room_id=None, day=DAYS[di],
                            start_period=ONLINE_PERIOD, duration=1,
                        )
                    )
    return out


def solve(
    courses: list[CourseInput],
    rooms: list[RoomInput],
    fixed_slots: list[dict] = None,
    min_candidates: int = 3,
    timeout_seconds: int = 30,
) -> list[TimetableResult]:
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        logger.warning("OR-Tools not found.")
        return []

    # The model is expensive to build, so build it exactly once and reuse it
    # for both phases; Phase 2 only adds constraints.
    build_started = time.monotonic()
    model, x, y, obj_var = build_model(courses, rooms, fixed_slots)
    build_seconds = time.monotonic() - build_started

    workers = os.cpu_count() or 8

    # Model building is not free at scale; charge it against the budget so the
    # solver is not handed a deadline that has already partly elapsed.
    solve_budget = max(10.0, timeout_seconds - build_seconds)
    phase1_time = max(5.0, solve_budget * 0.5)
    remaining = max(5.0, solve_budget - phase1_time)
    phase2_time = max(3.0, remaining / MAX_PHASE2_ATTEMPTS)

    # ── Phase 1: maximize ─────────────────────────────────────────────────────
    model.maximize(obj_var)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = phase1_time
    solver.parameters.num_search_workers = workers

    status = solver.solve(model)
    if status == cp_model.INFEASIBLE:
        logger.warning("Phase 1: 제약을 모두 만족하는 시간표가 존재하지 않습니다.")
        return []
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # UNKNOWN/MODEL_INVALID — out of time, NOT proof that no timetable exists.
        raise SolverTimeoutError(
            f"제한 시간({timeout_seconds}초) 안에 시간표를 찾지 못했습니다. "
            f"강의 {len(courses)}개 · 강의실 {len(rooms)}개 규모에서는 시간이 더 필요합니다 "
            f"(모델 생성에만 {build_seconds:.0f}초 소요). "
            "제약조건 문제가 아니라 계산 시간 문제이므로, "
            "ALGORITHM_TIMEOUT_SECONDS 값을 늘린 뒤 다시 시도하세요."
        )

    best_obj = int(solver.objective_value)
    logger.info(f"Phase 1 완료. 최고 목적함수 값: {best_obj}")

    results: list[TimetableResult] = []
    assignments = _extract_assignments(solver, x, y, courses)
    score, pref_rate, fitness_rate, conflicts = compute_score(assignments, courses, rooms)
    results.append(
        TimetableResult(
            assignments=assignments,
            score=score,
            pref_rate=pref_rate,
            fitness_rate=fitness_rate,
            conflict_count=conflicts,
        )
    )

    # ── Phase 2: diverse near-optimal candidates ──────────────────────────────
    # Drop the objective (Phase 2 is a satisfaction problem) and require every
    # new solution to differ from *all* previous ones by at least 10% of slots.
    model.clear_objective()
    tolerance = max(50, abs(best_obj) // 5)
    model.add(obj_var >= best_obj - tolerance)

    cut_added = False
    for seed in range(1, MAX_PHASE2_ATTEMPTS + 1):
        if len(results) >= min_candidates:
            break

        # Only cut away a solution we actually found; a timed-out attempt must
        # not narrow the search space further.
        if not cut_added:
            prev_true = [v for v in x.values() if solver.value(v)]
            if not prev_true:
                break
            min_diff = max(1, len(prev_true) // 10)
            model.add(sum(prev_true) <= len(prev_true) - min_diff)
            cut_added = True

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = phase2_time
        solver.parameters.num_search_workers = workers
        solver.parameters.random_seed = seed * 17 + 3
        solver.parameters.randomize_search = True

        status = solver.solve(model)
        if status == cp_model.INFEASIBLE:
            logger.info("Phase 2: 허용 점수 범위 내에 더 이상 다른 후보가 없습니다.")
            break
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # UNKNOWN — timed out. Retry with a different seed.
            logger.info(f"Phase 2 시도 {seed}: {solver.status_name(status)} — 재시도")
            continue

        cut_added = False
        assignments = _extract_assignments(solver, x, y, courses)
        s, p, f, cf = compute_score(assignments, courses, rooms)
        results.append(
            TimetableResult(
                assignments=assignments,
                score=s,
                pref_rate=p,
                fitness_rate=f,
                conflict_count=cf,
            )
        )
        logger.info(f"Phase 2 후보 {len(results)}: score={s:.1f}")

    if len(results) < min_candidates:
        logger.warning(
            f"요청 {min_candidates}개 중 서로 다른 후보 {len(results)}개만 생성되었습니다."
        )

    results.sort(key=lambda r: r.score, reverse=True)
    logger.info(f"solve() 후보 {len(results)}개 반환.")
    return results[:min_candidates]
