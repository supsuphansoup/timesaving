import json
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from ..database import get_db
from ..config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from ..models import User, AuditLog
from ..schemas import LoginRequest, Token, PasswordChangeRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

import hashlib

def get_password_hash(password: str) -> str:
    return hashlib.sha256(f"dongseo_salt_{password}".encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password




def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        user = User(
            username="admin",
            password_hash=get_password_hash("password123!"),
            name="김조교 (컴공과)",
            role="TA"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    # 데모 계정 하드코딩: admin / password123! 이면 무조건 로그인 성공
    if req.username == "admin" and req.password == "password123!":
        # DB에 admin 유저가 없으면 자동 생성
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            user = User(
                username="admin",
                password_hash=get_password_hash("password123!"),
                name="김조교 (컴공과)",
                role="TA"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        log = AuditLog(
            username=user.username,
            category="LOGIN",
            message=f"조교 로그인 성공 ({user.name})",
            details=json.dumps({"result": "SUCCESS"})
        )
        db.add(log)
        db.commit()

        token = create_access_token(data={"sub": user.username})
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user.username,
            "name": user.name
        }

    # 그 외 계정은 DB 조회
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        log = AuditLog(
            username=req.username,
            category="LOGIN",
            message=f"로그인 실패 (아이디: {req.username})",
            details=json.dumps({"result": "FAIL", "reason": "존재하지 않는 아이디"})
        )
        db.add(log)
        db.commit()
        raise HTTPException(status_code=400, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    # Audit Log: Success login
    log = AuditLog(
        username=user.username,
        category="LOGIN",
        message=f"조교 로그인 성공 ({user.name})",
        details=json.dumps({"result": "SUCCESS"})
    )
    db.add(log)
    db.commit()

    token = create_access_token(data={"sub": user.username})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "name": user.name
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/password", response_model=dict)
def change_password(
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="기존 비밀번호가 올바르지 않습니다.")

    current_user.password_hash = get_password_hash(req.new_password)
    
    # Audit log
    log = AuditLog(
        username=current_user.username,
        category="UPDATE",
        message=f"비밀번호 변경 완료 ({current_user.name})"
    )
    db.add(log)
    db.commit()

    return {"message": "비밀번호가 성공적으로 변경되었습니다."}
