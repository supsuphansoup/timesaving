import json
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import User, Semester, Professor, Room, Course, AuditLog
from .routers.auth import get_password_hash

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # 1. Create Default TA Account
    ta_user = db.query(User).filter(User.username == "admin").first()
    if not ta_user:
        ta_user = User(
            username="admin",
            password_hash=get_password_hash("password123!"),
            name="김조교 (컴공과)",
            role="TA"
        )
        db.add(ta_user)
        db.commit()

    # 2. Create Active Semester
    sem = db.query(Semester).filter(Semester.year == 2026, Semester.term == "1학기").first()
    if not sem:
        sem = Semester(year=2026, term="1학기", is_active=True)
        db.add(sem)
        db.commit()
        db.refresh(sem)

    # 3. Create Classrooms
    if db.query(Room).count() == 0:
        rooms_data = [
            Room(name="NM-301", building="뉴밀레니엄관", capacity=50, is_computer_lab=False, is_common=False, notes="기초강의실"),
            Room(name="NM-302", building="뉴밀레니엄관", capacity=45, is_computer_lab=False, is_common=False, notes="중형강의실"),
            Room(name="IT-501", building="정보공학관", capacity=40, is_computer_lab=True, is_common=False, notes="고성능 PC 실습실 A"),
            Room(name="IT-502", building="정보공학관", capacity=40, is_computer_lab=True, is_common=False, notes="고성능 PC 실습실 B"),
            Room(name="GL-101", building="글로벌관", capacity=80, is_computer_lab=False, is_common=True, notes="계단식 공용 대강의실"),
            Room(name="GL-102", building="글로벌관", capacity=60, is_computer_lab=False, is_common=True, notes="중형 공용강의실"),
        ]
        db.add_all(rooms_data)
        db.commit()

    r_nm301 = db.query(Room).filter(Room.name == "NM-301").first()
    r_it502 = db.query(Room).filter(Room.name == "IT-502").first()

    # 4. Create Professors
    if db.query(Professor).count() == 0:
        profs_data = [
            Professor(
                semester_id=sem.id,
                name="김동서",
                department="컴퓨터공학과",
                phone="051-320-1001",
                email="ds.kim@dongseo.ac.kr",
                unavailable_days=json.dumps(["금"]),
                preferred_days=json.dumps(["월", "수"]),
                unavailable_periods=json.dumps([1, 9]),
                preferred_periods=json.dumps([2, 3, 4]),
                fixed_room_id=r_nm301.id if r_nm301 else None,
                unavailable_room_ids=json.dumps([]),
                weekly_hours_limit=15
            ),
            Professor(
                semester_id=sem.id,
                name="이정보",
                department="정보통신공학과",
                phone="051-320-1002",
                email="jb.lee@dongseo.ac.kr",
                unavailable_days=json.dumps([]),
                preferred_days=json.dumps(["화", "목"]),
                unavailable_periods=json.dumps([8, 9]),
                preferred_periods=json.dumps([3, 4, 5]),
                fixed_room_id=None,
                unavailable_room_ids=json.dumps([]),
                weekly_hours_limit=15
            ),
            Professor(
                semester_id=sem.id,
                name="박인공",
                department="AI학부",
                phone="051-320-1003",
                email="ig.park@dongseo.ac.kr",
                unavailable_days=json.dumps(["수"]),
                preferred_days=json.dumps(["월", "화"]),
                unavailable_periods=json.dumps([1]),
                preferred_periods=json.dumps([2, 3, 4, 5]),
                fixed_room_id=None,
                unavailable_room_ids=json.dumps([]),
                weekly_hours_limit=12
            ),
            Professor(
                semester_id=sem.id,
                name="최미디어",
                department="디자인학부",
                phone="051-320-1004",
                email="md.choi@dongseo.ac.kr",
                unavailable_days=json.dumps(["월"]),
                preferred_days=json.dumps(["수", "목"]),
                unavailable_periods=json.dumps([]),
                preferred_periods=json.dumps([4, 5, 6]),
                fixed_room_id=None,
                unavailable_room_ids=json.dumps([]),
                weekly_hours_limit=12
            ),
            Professor(
                semester_id=sem.id,
                name="정게임",
                department="게임공학과",
                phone="051-320-1005",
                email="game.jung@dongseo.ac.kr",
                unavailable_days=json.dumps([]),
                preferred_days=json.dumps(["화", "수"]),
                unavailable_periods=json.dumps([1, 2]),
                preferred_periods=json.dumps([5, 6, 7]),
                fixed_room_id=r_it502.id if r_it502 else None,
                unavailable_room_ids=json.dumps([]),
                weekly_hours_limit=15
            ),
            Professor(
                semester_id=sem.id,
                name="강빅데이터",
                department="데이터승인학과",
                phone="051-320-1006",
                email="bd.kang@dongseo.ac.kr",
                unavailable_days=json.dumps(["목"]),
                preferred_days=json.dumps(["월", "금"]),
                unavailable_periods=json.dumps([]),
                preferred_periods=json.dumps([2, 3, 4]),
                fixed_room_id=None,
                unavailable_room_ids=json.dumps([]),
                weekly_hours_limit=12
            )
        ]
        db.add_all(profs_data)
        db.commit()

    p_kim = db.query(Professor).filter(Professor.name == "김동서").first()
    p_lee = db.query(Professor).filter(Professor.name == "이정보").first()
    p_park = db.query(Professor).filter(Professor.name == "박인공").first()
    p_choi = db.query(Professor).filter(Professor.name == "최미디어").first()
    p_jung = db.query(Professor).filter(Professor.name == "정게임").first()
    p_kang = db.query(Professor).filter(Professor.name == "강빅데이터").first()

    # 5. Create Courses
    if db.query(Course).count() == 0 and p_kim:
        courses_data = [
            Course(semester_id=sem.id, name="자료구조", professor_id=p_kim.id, department="컴퓨터공학과", grade=2, section="A", weekly_hours=3, expected_students=45, computer_required=False),
            Course(semester_id=sem.id, name="알고리즘개론", professor_id=p_kim.id, department="컴퓨터공학과", grade=3, section="A", weekly_hours=3, expected_students=40, computer_required=False),
            Course(semester_id=sem.id, name="C프로그래밍실습", professor_id=p_kim.id, department="컴퓨터공학과", grade=1, section="A", weekly_hours=3, expected_students=35, computer_required=True),

            Course(semester_id=sem.id, name="데이터통신", professor_id=p_lee.id, department="정보통신공학과", grade=2, section="A", weekly_hours=3, expected_students=35, computer_required=False),
            Course(semester_id=sem.id, name="네트워크보안실습", professor_id=p_lee.id, department="정보통신공학과", grade=3, section="A", weekly_hours=3, expected_students=30, computer_required=True),

            Course(semester_id=sem.id, name="인공지능개론", professor_id=p_park.id, department="AI학부", grade=2, section="A", weekly_hours=3, expected_students=40, computer_required=False),
            Course(semester_id=sem.id, name="머신러닝실습", professor_id=p_park.id, department="AI학부", grade=3, section="A", weekly_hours=3, expected_students=35, computer_required=True),
            Course(semester_id=sem.id, name="딥러닝응용", professor_id=p_park.id, department="AI학부", grade=4, section="A", weekly_hours=3, expected_students=30, computer_required=True),

            Course(semester_id=sem.id, name="디자인기하학", professor_id=p_choi.id, department="디자인학부", grade=1, section="A", weekly_hours=3, expected_students=50, computer_required=False),
            Course(semester_id=sem.id, name="디지털CG실습", professor_id=p_choi.id, department="디자인학부", grade=2, section="A", weekly_hours=3, expected_students=38, computer_required=True),

            Course(semester_id=sem.id, name="게임프로그래밍", professor_id=p_jung.id, department="게임공학과", grade=2, section="A", weekly_hours=3, expected_students=35, computer_required=True),
            Course(semester_id=sem.id, name="3D유니티실습", professor_id=p_jung.id, department="게임공학과", grade=3, section="A", weekly_hours=3, expected_students=35, computer_required=True),

            Course(semester_id=sem.id, name="빅데이터분석실습", professor_id=p_kang.id, department="데이터승인학과", grade=3, section="A", weekly_hours=3, expected_students=30, computer_required=True),
            Course(semester_id=sem.id, name="통계학개론", professor_id=p_kang.id, department="데이터승인학과", grade=1, section="A", weekly_hours=3, expected_students=55, computer_required=False),
        ]
        db.add_all(courses_data)
        db.commit()

    # 6. Create Initial Audit Log
    if db.query(AuditLog).count() == 0:
        db.add(AuditLog(
            username="admin",
            category="LOGIN",
            message="동서대학교 강의실 시간표 배정 시스템 초기 데이터베이스 초기화 완료"
        ))
        db.commit()

    db.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
