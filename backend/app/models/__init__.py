# models package
from app.models.user import User
from app.models.semester import Semester
from app.models.professor import Professor
from app.models.room import Room
from app.models.course import Course
from app.models.timetable import Timetable, Assignment
from app.models.log import Log

__all__ = [
    "User",
    "Semester",
    "Professor",
    "Room",
    "Course",
    "Timetable",
    "Assignment",
    "Log",
]
