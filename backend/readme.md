# 동서대학교 강의실 시간표 배정 시스템 — Backend

FastAPI + SQLAlchemy + OR-Tools CP-SAT 기반 강의실 시간표 자동 배정 REST API 서버입니다.

## 기술스택

| 역할 | 기술 |
|------|------|
| 웹 프레임워크 | FastAPI 0.111 |
| ORM / DB | SQLAlchemy 2 + SQLite(개발) / PostgreSQL(운영) |
| 인증 | itsdangerous 서명 세션 쿠키 + bcrypt |
| 알고리즘 | Google OR-Tools CP-SAT |
| 비동기 작업 | FastAPI BackgroundTasks + ThreadPoolExecutor |
| 내보내기 | openpyxl (Excel), reportlab (PDF) |

## 빠른 시작

```bash
# 1. 가상환경 생성
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 2. 의존성 설치
pip install -r requirements.txt

# 3. DB 초기화 및 관리자 계정 생성
python init_db.py

# 4. 개발 서버 실행
uvicorn app.main:app --reload
```

서버 기동 후 http://localhost:8000/docs 에서 Swagger UI를 확인할 수 있습니다.

## 초기 로그인 정보

| 항목 | 값 |
|------|-----|
| 아이디 | `admin` |
| 비밀번호 | `admin1234` |

> ⚠️ 첫 로그인 후 반드시 비밀번호를 변경하세요.

## API 구조

```
Base URL: /api/v1

POST   /auth/login              로그인
POST   /auth/logout             로그아웃
PUT    /auth/password           비밀번호 변경

GET    /professors              교수 목록 조회
POST   /professors              교수 등록
PUT    /professors/{id}         교수 수정
DELETE /professors/{id}         교수 삭제

GET    /rooms                   강의실 목록 조회
POST   /rooms                   강의실 등록
PUT    /rooms/{id}              강의실 수정
DELETE /rooms/{id}              강의실 삭제

GET    /courses                 강의 목록 조회
POST   /courses                 강의 등록
PUT    /courses/{id}            강의 수정
DELETE /courses/{id}            강의 삭제

POST   /timetables/generate     시간표 자동 생성 (비동기)
GET    /timetables/tasks/{id}   생성 작업 상태 폴링
GET    /timetables/candidates   추천안 목록
GET    /timetables/views        조건별 시간표 조회
POST   /timetables/validate-move 수동 변경 충돌 검증
POST   /timetables/reassign     부분 재배정
POST   /timetables/{id}/draft   임시 저장
POST   /timetables/{id}/confirm 최종 확정
GET    /timetables/{id}/export  PDF/Excel 내보내기
GET    /timetables/{id}         시간표 상세 조회

GET    /logs                    이력 로그 조회
```

## 환경변수 (.env)

| 키 | 기본값 | 설명 |
|----|--------|------|
| `DATABASE_URL` | `sqlite:///./timesaving.db` | DB 연결 URL |
| `SECRET_KEY` | (변경 필요) | 세션 쿠키 서명 키 |
| `CORS_ORIGINS` | `http://localhost:5173` | 허용 오리진 |
| `ALGORITHM_TIMEOUT_SECONDS` | `120` | 알고리즘 최대 실행 시간 |
