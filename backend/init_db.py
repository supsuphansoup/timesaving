"""
Database initialisation and seed script.

Run once after installing dependencies:
    python init_db.py

Creates all tables and inserts the initial admin account + default semester.
"""

import os
import shutil
from datetime import datetime

from sqlalchemy import inspect, text

from app.database import Base, SessionLocal, engine
import app.models  # noqa: F401 — ensure all models are registered with Base

from app.config import settings
from app.models.user import User
from app.models.semester import Semester
from app.services.auth_service import hash_password


def _backup_sqlite_file() -> None:
    """Copy the SQLite file next to itself before any schema surgery."""
    url = str(engine.url)
    if not url.startswith("sqlite"):
        return
    path = engine.url.database
    if not path or path == ":memory:" or not os.path.exists(path):
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = f"{path}.{stamp}.bak"
    shutil.copy2(path, dest)
    print(f"[BACKUP] {dest}")


def _recover_interrupted_rebuild(insp) -> None:
    """
    Finish (or undo) an ``assignments`` rebuild that died half-way.

    A previous crash can leave a new empty ``assignments`` plus the populated
    ``assignments_old``. Without this the data is silently stranded.
    """
    tables = set(insp.get_table_names())
    if "assignments_old" not in tables:
        return

    with engine.begin() as conn:
        old_n = conn.execute(text("SELECT COUNT(*) FROM assignments_old")).scalar()
        new_n = (
            conn.execute(text("SELECT COUNT(*) FROM assignments")).scalar()
            if "assignments" in tables else 0
        )
        print(f"[RECOVER] 중단된 마이그레이션 감지 (assignments={new_n}행, assignments_old={old_n}행)")

        if "assignments" not in tables:
            conn.execute(text("ALTER TABLE assignments_old RENAME TO assignments"))
            print("[RECOVER] assignments_old를 되돌렸습니다.")
            return

        if new_n == 0 and old_n > 0:
            conn.execute(text(
                "INSERT INTO assignments"
                " (id, timetable_id, course_id, room_id, day, start_period,"
                "  duration, is_locked, created_at, updated_at)"
                " SELECT id, timetable_id, course_id, room_id, day, start_period,"
                "        COALESCE(duration, 1), COALESCE(is_locked, 0),"
                "        COALESCE(created_at, CURRENT_TIMESTAMP),"
                "        COALESCE(updated_at, CURRENT_TIMESTAMP)"
                " FROM assignments_old"
            ))
            print(f"[RECOVER] {old_n}행을 복구했습니다.")
        conn.execute(text("DROP TABLE assignments_old"))


def migrate() -> None:
    """
    Bring an existing database up to date.

    ``Base.metadata.create_all`` only creates *missing* tables — it never alters
    an existing one. Without this step an older timesaving.db keeps the old
    schema and fails at runtime, so each change is applied idempotently here.
    """
    insp = inspect(engine)
    if "courses" not in insp.get_table_names():
        return  # fresh database — create_all() already produced the new schema

    # sqlite3 autocommits DDL, so a mid-way failure is NOT rolled back. Take a
    # copy first and recover from a half-finished previous attempt if needed.
    _backup_sqlite_file()
    _recover_interrupted_rebuild(insp)

    insp = inspect(engine)
    with engine.begin() as conn:
        # 1) courses.online_hours (온라인 수업 시수)
        cols = {c["name"] for c in insp.get_columns("courses")}
        if "online_hours" not in cols:
            conn.execute(text(
                "ALTER TABLE courses ADD COLUMN online_hours INTEGER NOT NULL DEFAULT 0"
            ))
            print("[MIGRATE] courses.online_hours 컬럼 추가")

        # 2) assignments.room_id NOT NULL -> NULL (온라인 수업은 강의실이 없음)
        a_cols = {c["name"]: c for c in insp.get_columns("assignments")}
        if "room_id" in a_cols and not a_cols["room_id"]["nullable"]:
            # SQLite cannot ALTER a column's nullability; rebuild the table.
            # NOTE: RENAME TO keeps the old indexes under their original names,
            # so they must be dropped or re-creating the table collides with them.
            old_indexes = [
                row[0] for row in conn.execute(text(
                    "SELECT name FROM sqlite_master"
                    " WHERE type='index' AND tbl_name='assignments'"
                    "   AND name NOT LIKE 'sqlite_autoindex%'"
                )).fetchall()
            ]
            conn.execute(text("ALTER TABLE assignments RENAME TO assignments_old"))
            for idx in old_indexes:
                conn.execute(text(f'DROP INDEX IF EXISTS "{idx}"'))
            Base.metadata.tables["assignments"].create(bind=conn)
            conn.execute(text(
                "INSERT INTO assignments"
                " (id, timetable_id, course_id, room_id, day, start_period,"
                "  duration, is_locked, created_at, updated_at)"
                " SELECT id, timetable_id, course_id, room_id, day, start_period,"
                "        COALESCE(duration, 1), COALESCE(is_locked, 0),"
                "        COALESCE(created_at, CURRENT_TIMESTAMP),"
                "        COALESCE(updated_at, CURRENT_TIMESTAMP)"
                " FROM assignments_old"
            ))
            moved = conn.execute(text("SELECT COUNT(*) FROM assignments")).scalar()
            orig = conn.execute(text("SELECT COUNT(*) FROM assignments_old")).scalar()
            if moved != orig:
                raise RuntimeError(
                    f"배정 데이터 이관 실패: {orig}행 중 {moved}행만 복사됨. "
                    "assignments_old를 남겨두니 확인 후 수동 복구하세요."
                )
            conn.execute(text("DROP TABLE assignments_old"))
            print(f"[MIGRATE] assignments.room_id를 NULL 허용으로 변경 ({moved}행 이관 완료)")


def init(reset: bool = False):
    print("[*] Creating database tables...")
    if reset:
        print("[!] --reset flag: dropping all tables first...")
        Base.metadata.drop_all(bind=engine)
        print("[OK] All tables dropped")
    else:
        migrate()
    Base.metadata.create_all(bind=engine)
    print("[OK] Tables created")


    db = SessionLocal()
    try:
        # ── Admin user ────────────────────────────────────────────
        existing = db.query(User).filter(User.username == settings.init_admin_username).first()
        if existing:
            print(f"[INFO] Admin account '{settings.init_admin_username}' already exists.")
        else:
            admin = User(
                username=settings.init_admin_username,
                hashed_password=hash_password(settings.init_admin_password),
            )
            db.add(admin)
            db.commit()
            print("[OK] Admin account created.")
            print(f"     username : {settings.init_admin_username}")
            print(f"     password : {settings.init_admin_password}")
            print("[!!] Change the password after first login!")

        # ── Default semester (2025-1) ─────────────────────────────
        sem = db.query(Semester).filter(Semester.year == 2025, Semester.term == 1).first()
        if not sem:
            sem = Semester(name="2025년 1학기", year=2025, term=1, is_active=True)
            db.add(sem)
            db.commit()
            db.refresh(sem)
            print(f"[OK] Default semester created: id={sem.id} ({sem.name})")
        else:
            print(f"[INFO] Default semester already exists: id={sem.id}")

    finally:
        db.close()



if __name__ == "__main__":
    import sys
    init(reset="--reset" in sys.argv)
