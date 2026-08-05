import datetime
import json
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(50), nullable=False, default="조교")
    role = Column(String(20), default="TA")  # 조교 단일 사용자
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Semester(Base):
    __tablename__ = "semesters"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, default=2026)
    term = Column(String(20), nullable=False, default="1학기")  # 1학기, 2학기, 여름학기, 겨울학기
    is_active = Column(Boolean, default=True)

class Professor(Base):
    __tablename__ = "professors"

    id = Column(Integer, primary_key=True, index=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, default=1)
    name = Column(String(50), nullable=False)
    department = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    
    # 6개 교수 제약조건 + 주당 시수
    unavailable_days = Column(Text, default="[]")      # JSON List e.g. ["월", "금"]
    preferred_days = Column(Text, default="[]")        # JSON List e.g. ["화", "목"]
    unavailable_periods = Column(Text, default="[]")   # JSON List e.g. [1, 2, 8, 9]
    preferred_periods = Column(Text, default="[]")     # JSON List e.g. [3, 4, 5, 6]
    unavailable_slots = Column(Text, default="[]")     # JSON List e.g. ["월-1", "화-3"]
    preferred_slots = Column(Text, default="[]")       # JSON List e.g. ["수-5", "목-6"]
    fixed_room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)  # 강의실 픽스
    unavailable_room_ids = Column(Text, default="[]") # JSON List e.g. [2, 5]
    weekly_hours_limit = Column(Integer, default=15)    # 주당 최대 시수

    fixed_room = relationship("Room", foreign_keys=[fixed_room_id])
    courses = relationship("Course", back_populates="professor", cascade="all, delete-orphan")

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # e.g., "NM-301", "IT-502"
    building = Column(String(100), nullable=False) # e.g., "뉴밀레니엄관", "정보공학관"
    capacity = Column(Integer, nullable=False, default=40)
    is_computer_lab = Column(Boolean, default=False) # 컴퓨터실 여부
    is_common = Column(Boolean, default=False)       # 공용 강의실 여부
    available_hours = Column(Text, default="[]")     # JSON list of dict or periods
    unavailable_hours = Column(Text, default="[]")   # JSON list of dict e.g. [{"day": "수", "periods": [1,2]}]
    notes = Column(Text, nullable=True)

    courses = relationship("Course", back_populates="fixed_room", foreign_keys="Course.fixed_room_id")

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, default=1)
    name = Column(String(100), nullable=False)        # 과목명
    professor_id = Column(Integer, ForeignKey("professors.id"), nullable=False)
    department = Column(String(100), nullable=False)  # 소속 학과
    grade = Column(Integer, nullable=False, default=1) # 대상 학년 (1~4)
    section = Column(String(20), nullable=False, default="A") # 분반 (A, B, C...)
    weekly_hours = Column(Integer, nullable=False, default=3) # 주당 시수 (e.g. 3시간)
    expected_students = Column(Integer, nullable=False, default=30) # 예상 수강 인원
    computer_required = Column(Boolean, default=False) # 컴퓨터 필요 여부 (Hard)
    fixed_room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True) # 특정 고정 강의실(선택)

    professor = relationship("Professor", back_populates="courses")
    fixed_room = relationship("Room", foreign_keys=[fixed_room_id])

class TimetableCandidate(Base):
    __tablename__ = "timetable_candidates"

    id = Column(Integer, primary_key=True, index=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, default=1)
    name = Column(String(100), nullable=False)        # e.g., "추천안 1 (선호도 최적안)"
    status = Column(String(20), default="CANDIDATE")  # CANDIDATE, CONFIRMED
    total_score = Column(Float, default=100.0)
    satisfaction_rate = Column(Float, default=95.0)   # 선호도 반영률 (%)
    satisfied_soft_constraints = Column(Integer, default=10) # 만족한 Soft Constraint 수
    conflict_count = Column(Integer, default=0)       # 하드 제약 충돌 수 (정상 생성 시 0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    assignments = relationship("TimetableAssignment", back_populates="candidate", cascade="all, delete-orphan")

class TimetableAssignment(Base):
    __tablename__ = "timetable_assignments"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("timetable_candidates.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    day = Column(String(10), nullable=False)          # "월", "화", "수", "목", "금"
    start_period = Column(Integer, nullable=False)    # 1 ~ 9교시
    duration = Column(Integer, nullable=False)        # 연강 시간 (e.g., 3)
    is_locked = Column(Boolean, default=False)        # 수동 고정 여부 (부분 재배정 시 유지)

    candidate = relationship("TimetableCandidate", back_populates="assignments")
    course = relationship("Course")
    room = relationship("Room")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    username = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)     # "LOGIN", "GENERATE", "UPDATE", "CONFIRM"
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)             # JSON details
