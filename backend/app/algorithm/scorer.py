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
    """
    course_map = {c.id: c for c in courses}

    total_soft = 0.0
    satisfied_soft = 0.0
    conflict_count = 0
    engine_score = 0.0

    room_slots: dict[tuple, int] = {}
    prof_slots: dict[tuple, int] = {}
    course_slots = {}
    course_rooms = {}

    for a in assignments:
        c = course_map.get(a.course_id)
        if not c:
            continue
            
        course_slots.setdefault(a.course_id, []).append((a.day, a.start_period))
        course_rooms.setdefault(a.course_id, set()).add(a.room_id)
        
        # Conflict detection
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

        # ── Engine Score Calculation (Match engine.py exactly) ──
        if a.day in c.preferred_days:
            engine_score += 15
        if a.start_period in c.preferred_periods:
            engine_score += 10
        if a.day in c.non_preferred_days:
            engine_score -= 15
        if a.start_period in c.non_preferred_periods:
            engine_score -= 10
        if a.start_period in [4, 5]:
            engine_score -= 5

        # ── Satisfaction Rate Calculation ──
        # Only count if the professor actually specified preferences!
        if c.preferred_days:
            total_soft += 1.0
            if a.day in c.preferred_days:
                satisfied_soft += 1.0
                
        if c.preferred_periods:
            total_soft += 1.0
            if a.start_period in c.preferred_periods:
                satisfied_soft += 1.0
                
        if c.non_preferred_days:
            total_soft += 1.0
            if a.day not in c.non_preferred_days:
                satisfied_soft += 1.0
                
        if c.non_preferred_periods:
            total_soft += 1.0
            if a.start_period not in c.non_preferred_periods:
                satisfied_soft += 1.0

        # Lunchtime (always applies)
        total_soft += 1.0
        if a.start_period not in [4, 5]:
            satisfied_soft += 1.0

    # ── Advanced Features: Consecutive Periods & Room Consistency ──
    for c_id, slots in course_slots.items():
        c = course_map[c_id]
        
        # Room Consistency: Penalty for multiple rooms
        rooms_used = len(course_rooms.get(c_id, set()))
        if rooms_used > 1:
            engine_score -= (rooms_used - 1) * 10
            
        consecutive_pairs = 0
        slots_by_day = {}
        for day, period in slots:
            slots_by_day.setdefault(day, []).append(period)
            
        for day, periods in slots_by_day.items():
            periods.sort()
            for i in range(len(periods) - 1):
                if periods[i+1] == periods[i] + 1:
                    consecutive_pairs += 1
                    
        max_possible = max(0, c.weekly_hours - 1)
        if max_possible > 0:
            total_soft += max_possible
            satisfied_soft += consecutive_pairs
            engine_score += consecutive_pairs * 20

    # SC-06 Professor daily load balancing
    prof_day_slots = {}
    for a in assignments:
        c = course_map.get(a.course_id)
        if c:
            prof_day_slots.setdefault(c.professor_id, {}).setdefault(a.day, 0)
            prof_day_slots[c.professor_id][a.day] += 1
            
    for p_id, day_counts in prof_day_slots.items():
        for day, count in day_counts.items():
            if count > 4:
                excess = count - 4
                engine_score -= excess * 10

    csr = satisfied_soft / total_soft if total_soft > 0 else 0.0
    
    return engine_score, csr, conflict_count
