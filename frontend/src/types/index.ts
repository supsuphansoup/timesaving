export interface User {
  id: number;
  username: string;
  name: string;
  role: string;
}

export interface Professor {
  id: number;
  semester_id: number;
  name: string;
  employee_number: string;
  department: string;
}

export interface Room {
  id: number;
  name: string;
  building: string;
  capacity: number;
  is_computer_lab: boolean;
  is_common: boolean;
  notes?: string;
}

export interface Course {
  id: number;
  semester_id: number;
  course_name: string;
  professor_id: number;
  department: string;
  target_grade: number;
  class_section: string;
  weekly_hours: number;
  expected_students: number;
  requires_computer: boolean;
  preferred_days: string[];
  non_preferred_days: string[];
  preferred_periods: number[];
  non_preferred_periods: number[];
  fixed_room_ids: number[];
  professor_name?: string;
  fixed_room_name?: string;
}

export interface Assignment {
  id: number;
  course_id: number;
  room_id: number;
  day: string;
  start_period: number;
  duration: number;
  is_locked: boolean;
  course_name: string;
  professor_id: number;
  professor_name: string;
  department: string;
  grade: number;
  section: string;
  room_name: string;
  building: string;
  is_computer_lab: boolean;
}

export interface Candidate {
  id: number;
  semester_id: number;
  name?: string;
  status: string;
  score: number;
  constraint_satisfaction_rate: number;
  conflict_count: number;
  created_at: string;
  assignments: Assignment[];
}

export interface AuditLogItem {
  id: number;
  timestamp: string;
  username: string;
  category: 'LOGIN' | 'GENERATE' | 'UPDATE' | 'CONFIRM';
  message: string;
  details?: string;
}
