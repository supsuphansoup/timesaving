"""
Database initialisation and seed script.

Run once after installing dependencies:
    python init_db.py

Creates all tables and inserts the initial admin account + default semester.
"""

from app.database import Base, SessionLocal, engine
import app.models  # noqa: F401 — ensure all models are registered with Base

from app.config import settings
from app.models.user import User
from app.models.semester import Semester
from app.services.auth_service import hash_password


def init(reset: bool = False):
    print("[*] Creating database tables...")
    if reset:
        print("[!] --reset flag: dropping all tables first...")
        Base.metadata.drop_all(bind=engine)
        print("[OK] All tables dropped")
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
