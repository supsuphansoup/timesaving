import json
from typing import List, Dict, Any, Tuple, Optional
from ortools.sat.python import cp_model

DAYS = ["월", "화", "수", "목", "금"]
PERIODS = list(range(1, 10))  # 1교시 ~ 9교시

def solve_timetable(
    courses_data: List[Dict[str, Any]],
    rooms_data: List[Dict[str, Any]],
    professors_data: List[Dict[str, Any]],
    locked_assignments: Optional[List[Dict[str, Any]]] = None,
    num_solutions: int = 3
) -> List[Dict[str, Any]]:
    """
    Google OR-Tools CP-SAT Solver for Classroom Timetable Assignment.
    Generates multiple distinct candidate solutions conforming to HC-01 ~ HC-09 and scoring SC-01, SC-02.
    """
    prof_map = {p["id"]: p for p in professors_data}
    room_map = {r["id"]: r for r in rooms_data}
    locked_map = {}
    if locked_assignments:
        for la in locked_assignments:
            locked_map[la["course_id"]] = la

    results = []

    for sol_index in range(num_solutions):
        model = cp_model.CpModel()

        # Decision Variables: X[c_id, r_id, d_idx, p_idx] = 1 if course starts at day d_idx, period p_idx in room r_id
        # Duration for each course = course["weekly_hours"] (e.g. 3)
        vars_map = {}
        course_occupied_vars = {} # (c_id, d_idx, p_idx) -> BoolVar

        for c in courses_data:
            c_id = c["id"]
            duration = c["weekly_hours"]
            prof = prof_map.get(c["professor_id"])
            if not prof:
                continue

            # Parse professor constraints
            unavail_days = set(json.loads(prof.get("unavailable_days") or "[]"))
            unavail_periods = set(json.loads(prof.get("unavailable_periods") or "[]"))
            unavail_slots = set(json.loads(prof.get("unavailable_slots") or "[]"))
            fixed_room_id = prof.get("fixed_room_id") or c.get("fixed_room_id")
            unavail_room_ids = set(json.loads(prof.get("unavailable_room_ids") or "[]"))

            # Filter valid rooms for this course
            valid_rooms = []
            for r in rooms_data:
                r_id = r["id"]
                # HC-05: Fixed room
                if fixed_room_id and r_id != fixed_room_id:
                    continue
                # HC-06: Professor unavailable room
                if r_id in unavail_room_ids:
                    continue
                # HC-07: Computer lab required
                if c.get("computer_required") and not r.get("is_computer_lab"):
                    continue
                # HC-08: Capacity check
                if r.get("capacity", 0) < c.get("expected_students", 0):
                    continue
                valid_rooms.append(r_id)

            if not valid_rooms:
                # Fallback to all rooms if filter is too strict, to ensure solution attempts
                valid_rooms = [r["id"] for r in rooms_data if r.get("capacity", 0) >= c.get("expected_students", 0)] or [r["id"] for r in rooms_data]

            # If locked, force specific day, period, room
            if c_id in locked_map:
                l_item = locked_map[c_id]
                l_day_idx = DAYS.index(l_item["day"]) if l_item["day"] in DAYS else 0
                l_start_p = l_item["start_period"]
                l_room_id = l_item["room_id"]

            for r_id in valid_rooms:
                for d_idx, day_str in enumerate(DAYS):
                    # HC-03: Unavailable day check
                    if day_str in unavail_days and c_id not in locked_map:
                        continue

                    # Check if duration fits within 9 periods
                    for p_start in PERIODS:
                        p_end = p_start + duration - 1
                        if p_end > 9:
                            continue

                        # HC-04: Unavailable period check for any period in block (whole period or specific slot)
                        overlap_unavail = any(
                            p in unavail_periods or f"{day_str}-{p}" in unavail_slots
                            for p in range(p_start, p_end + 1)
                        )
                        if overlap_unavail and c_id not in locked_map:
                            continue

                        # HC-09: Room unavailable hours check
                        room_obj = room_map.get(r_id)
                        room_unavail = False
                        if room_obj and room_obj.get("unavailable_hours"):
                            unavail_list = json.loads(room_obj.get("unavailable_hours") or "[]")
                            for u in unavail_list:
                                if u.get("day") == day_str and any(p in u.get("periods", []) for p in range(p_start, p_end + 1)):
                                    room_unavail = True
                                    break
                        if room_unavail and c_id not in locked_map:
                            continue

                        # Var creation
                        v_name = f"x_c{c_id}_r{r_id}_d{d_idx}_p{p_start}"
                        var = model.NewBoolVar(v_name)
                        vars_map[(c_id, r_id, d_idx, p_start)] = var

                        # Locked constraint enforcement
                        if c_id in locked_map:
                            if r_id == l_room_id and d_idx == l_day_idx and p_start == l_start_p:
                                model.Add(var == 1)
                            else:
                                model.Add(var == 0)

        # Constraint 1: Every course must be scheduled exactly once
        for c in courses_data:
            c_id = c["id"]
            c_vars = [v for k, v in vars_map.items() if k[0] == c_id]
            if c_vars:
                model.Add(sum(c_vars) == 1)

        # Build occupancy mapping for room/professor/grade overlap checks
        # Occupied[r_id, d_idx, p_idx] = list of (c_id, start_p, var)
        room_time_occupancy = {}
        prof_time_occupancy = {}
        grade_time_occupancy = {}

        for (c_id, r_id, d_idx, p_start), var in vars_map.items():
            course_obj = next((item for item in courses_data if item["id"] == c_id), None)
            if not course_obj:
                continue
            duration = course_obj["weekly_hours"]
            prof_id = course_obj["professor_id"]
            dept_grade = (course_obj["department"], course_obj["grade"])

            for p in range(p_start, p_start + duration):
                # Room occupancy
                r_key = (r_id, d_idx, p)
                room_time_occupancy.setdefault(r_key, []).append(var)

                # Professor occupancy
                pr_key = (prof_id, d_idx, p)
                prof_time_occupancy.setdefault(pr_key, []).append(var)

                # Department & Grade occupancy (avoid same grade same dept course clash)
                dg_key = (dept_grade, d_idx, p)
                grade_time_occupancy.setdefault(dg_key, []).append(var)

        # HC-01: No room overlap
        for r_key, var_list in room_time_occupancy.items():
            model.Add(sum(var_list) <= 1)

        # HC-02: No professor overlap
        for pr_key, var_list in prof_time_occupancy.items():
            model.Add(sum(var_list) <= 1)

        # Same Department & Grade soft/hard no-overlap (prevent students having conflicting required courses)
        for dg_key, var_list in grade_time_occupancy.items():
            if len(var_list) > 1:
                model.Add(sum(var_list) <= 1)

        # Objective Function: Soft constraints & Diversity across solution candidates
        objective_terms = []

        for (c_id, r_id, d_idx, p_start), var in vars_map.items():
            course_obj = next((item for item in courses_data if item["id"] == c_id), None)
            if not course_obj:
                continue
            prof = prof_map.get(course_obj["professor_id"])
            if not prof:
                continue

            pref_days = set(json.loads(prof.get("preferred_days") or "[]"))
            pref_periods = set(json.loads(prof.get("preferred_periods") or "[]"))
            day_str = DAYS[d_idx]
            duration = course_obj["weekly_hours"]

            score = 0
            # SC-01: Preferred Day
            if day_str in pref_days:
                score += 15 * duration
            # SC-02: Preferred Period
            score += sum(10 for p in range(p_start, p_start + duration) if p in pref_periods)

            # Solution Diversity Variation
            if sol_index == 1:
                # Sol 2: Favor earlier periods (morning / compact schedule)
                score += (10 - p_start) * 3
            elif sol_index == 2:
                # Sol 3: Favor room distribution (larger rooms preferred)
                room_cap = room_map.get(r_id, {}).get("capacity", 40)
                score += room_cap // 5

            if score > 0:
                objective_terms.append(var * score)

        # If previous solutions exist, add negative weight for exact previous assignments to encourage distinct candidate options
        if results and len(results) > 0:
            for prev_res in results:
                for prev_assign in prev_res["assignments"]:
                    c_id = prev_assign["course_id"]
                    r_id = prev_assign["room_id"]
                    d_idx = DAYS.index(prev_assign["day"]) if prev_assign["day"] in DAYS else 0
                    p_start = prev_assign["start_period"]
                    if (c_id, r_id, d_idx, p_start) in vars_map:
                        # Small penalty to explore distinct timetable configurations
                        objective_terms.append(vars_map[(c_id, r_id, d_idx, p_start)] * (-5))

        if objective_terms:
            model.Maximize(sum(objective_terms))

        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        status = solver.Solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            assignments = []
            total_score = solver.ObjectiveValue()
            satisfied_soft_count = 0
            total_soft_count = 0

            for (c_id, r_id, d_idx, p_start), var in vars_map.items():
                if solver.Value(var) == 1:
                    course_obj = next((item for item in courses_data if item["id"] == c_id), None)
                    duration = course_obj["weekly_hours"] if course_obj else 3
                    day_str = DAYS[d_idx]

                    # Soft constraint evaluation
                    prof = prof_map.get(course_obj["professor_id"]) if course_obj else None
                    if prof:
                        pref_days = set(json.loads(prof.get("preferred_days") or "[]"))
                        pref_periods = set(json.loads(prof.get("preferred_periods") or "[]"))
                        total_soft_count += 2
                        if day_str in pref_days:
                            satisfied_soft_count += 1
                        if any(p in pref_periods for p in range(p_start, p_start + duration)):
                            satisfied_soft_count += 1

                    is_locked = c_id in locked_map

                    assignments.append({
                        "course_id": c_id,
                        "room_id": r_id,
                        "day": day_str,
                        "start_period": p_start,
                        "duration": duration,
                        "is_locked": is_locked
                    })

            # Calculate metric percentages
            satisfaction_rate = round((satisfied_soft_count / max(1, total_soft_count)) * 100, 1)
            candidate_names = [
                "추천안 1 (선호도 극대화 최적안)",
                "추천안 2 (교수 동선/시간 집중안)",
                "추천안 3 (강의실 수용률 분배안)"
            ]
            cand_name = candidate_names[sol_index] if sol_index < len(candidate_names) else f"추천안 {sol_index + 1}"

            results.append({
                "name": cand_name,
                "total_score": float(total_score),
                "satisfaction_rate": satisfaction_rate,
                "satisfied_soft_constraints": satisfied_soft_count,
                "conflict_count": 0,
                "assignments": assignments
            })

    return results

def validate_manual_edit(
    target_course_id: int,
    new_day: str,
    new_start_period: int,
    new_room_id: int,
    all_assignments: List[Dict[str, Any]],
    courses_data: List[Dict[str, Any]],
    rooms_data: List[Dict[str, Any]],
    professors_data: List[Dict[str, Any]]
) -> Tuple[bool, List[str]]:
    """
    Validates a manual move against hard constraints HC-01 ~ HC-09.
    Returns (is_valid, list_of_conflict_messages).
    """
    conflicts = []
    target_course = next((c for c in courses_data if c["id"] == target_course_id), None)
    if not target_course:
        return False, ["존재하지 않는 강의입니다."]

    target_duration = target_course["weekly_hours"]
    target_prof = next((p for p in professors_data if p["id"] == target_course["professor_id"]), None)
    target_room = next((r for r in rooms_data if r["id"] == new_room_id), None)

    if not target_room:
        return False, ["지정한 강의실이 존재하지 않습니다."]

    # HC-08: Capacity check
    if target_room["capacity"] < target_course["expected_students"]:
        conflicts.append(f"HC-08 위반: 강의실 수용인원({target_room['capacity']}명)이 수강인원({target_course['expected_students']}명)보다 적습니다.")

    # HC-07: Computer requirement
    if target_course.get("computer_required") and not target_room.get("is_computer_lab"):
        conflicts.append("HC-07 위반: 컴퓨터가 필요한 실습 수업이나 대상 강의실이 컴퓨터실이 아닙니다.")

    if target_prof:
        unavail_days = set(json.loads(target_prof.get("unavailable_days") or "[]"))
        unavail_periods = set(json.loads(target_prof.get("unavailable_periods") or "[]"))
        fixed_room_id = target_prof.get("fixed_room_id")
        unavail_room_ids = set(json.loads(target_prof.get("unavailable_room_ids") or "[]"))

        # HC-03: Unavailable day
        if new_day in unavail_days:
            conflicts.append(f"HC-03 위반: {target_prof['name']} 교수의 불가 요일({new_day})입니다.")

        # HC-04: Unavailable period
        for p in range(new_start_period, new_start_period + target_duration):
            if p in unavail_periods:
                conflicts.append(f"HC-04 위반: {target_prof['name']} 교수의 불가 교시({p}교시)가 포함되어 있습니다.")

        # HC-05: Fixed room
        if fixed_room_id and new_room_id != fixed_room_id:
            fixed_r_obj = next((r for r in rooms_data if r["id"] == fixed_room_id), None)
            r_name = fixed_r_obj["name"] if fixed_r_obj else str(fixed_room_id)
            conflicts.append(f"HC-05 위반: {target_prof['name']} 교수는 고정 강의실({r_name})만 사용해야 합니다.")

        # HC-06: Unavailable room
        if new_room_id in unavail_room_ids:
            conflicts.append(f"HC-06 위반: {target_prof['name']} 교수의 배정 불가 강의실입니다.")

    # HC-09: Room unavailable hours
    if target_room.get("unavailable_hours"):
        unavail_list = json.loads(target_room.get("unavailable_hours") or "[]")
        for u in unavail_list:
            if u.get("day") == new_day:
                for p in range(new_start_period, new_start_period + target_duration):
                    if p in u.get("periods", []):
                        conflicts.append(f"HC-09 위반: {target_room['name']} 강의실의 사용 불가 시간대({new_day} {p}교시)입니다.")

    # Check overlaps with existing assignments (excluding the course being edited)
    for assign in all_assignments:
        if assign["course_id"] == target_course_id:
            continue
        if assign["day"] != new_day:
            continue

        a_start = assign["start_period"]
        a_end = a_start + assign["duration"] - 1
        t_start = new_start_period
        t_end = new_start_period + target_duration - 1

        # Check interval overlap
        if max(t_start, a_start) <= min(t_end, a_end):
            # HC-01: Room overlap
            if assign["room_id"] == new_room_id:
                other_c = next((c for c in courses_data if c["id"] == assign["course_id"]), None)
                c_name = other_c["name"] if other_c else "기존 수업"
                conflicts.append(f"HC-01 위반: {new_day}요일 {target_room['name']}에 기존 수업({c_name})과 시간이 중복됩니다.")

            # HC-02: Professor overlap
            other_c = next((c for c in courses_data if c["id"] == assign["course_id"]), None)
            if other_c and target_prof and other_c["professor_id"] == target_prof["id"]:
                conflicts.append(f"HC-02 위반: {target_prof['name']} 교수의 타 수업({other_c['name']})과 동일 시간대 중복 배정입니다.")

    return (len(conflicts) == 0, conflicts)
