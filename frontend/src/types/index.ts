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
  department: string;
  phone?: string;
  email?: string;
  unavailable_days: string[];
  preferred_days: string[];
  unavailable_periods: number[];
  preferred_periods: number[];
  unavailable_slots?: string[];
  preferred_slots?: string[];
  fixed_room_id?: number | null;
  unavailable_room_ids: number[];
  weekly_hours_limit: number;
}

export interface Room {
  id: number;
  name: string;
  building: string;
  capacity: number;
  is_computer_lab: boolean;
  is_common: boolean;
  available_hours: any[];
  unavailable_hours: { day: string; periods: number[] }[];
  notes?: string;
}

export interface Course {
  id: number;
  semester_id: number;
  name: string;
  professor_id: number;
  department: string;
  grade: number;
  section: string;
  weekly_hours: number;
  expected_students: number;
  computer_required: boolean;
  fixed_room_id?: number | null;
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
  name: string;
  status: 'CANDIDATE' | 'CONFIRMED';
  total_score: number;
  satisfaction_rate: number;
  satisfied_soft_constraints: number;
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
