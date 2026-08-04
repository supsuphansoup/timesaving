from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Return User if credentials are valid, else None."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> bool:
    """Change password. Returns False if old_password is wrong."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not verify_password(old_password, user.hashed_password):
        return False
    user.hashed_password = hash_password(new_password)
    db.commit()
    return True
