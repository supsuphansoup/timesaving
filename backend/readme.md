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
#    (기존 DB가 있으면 스키마 이관 migrate()가 자동 실행됩니다)
python init_db.py

#    처음부터 다시 만들려면 (모든 데이터 삭제)
# python init_db.py --reset

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
DELETE /courses/action/reset    강의 전체 초기화

POST   /timetables/generate     시간표 자동 생성 (비동기)
GET    /timetables/tasks/{id}   생성 작업 상태 폴링
GET    /timetables/candidates   추천안 목록
GET    /timetables/views        조건별 시간표 조회
POST   /timetables/validate-move 수동 변경 충돌 검증 (ER-01~ER-12)
POST   /timetables/manual-edit  수동 배정 변경
POST   /timetables/swap         두 배정 맞바꾸기
POST   /timetables/toggle-lock/{assignment_id}  배정 잠금 토글
POST   /timetables/reassign     부분 재배정 (잠근 배정 유지)
POST   /timetables/{id}/draft   임시 저장
POST   /timetables/{id}/confirm 최종 확정
GET    /timetables/{id}/export  PDF/Excel 내보내기 (학부 배포 양식)
GET    /timetables/{id}         시간표 상세 조회

GET    /logs                    이력 로그 조회
```

## 환경변수 (.env)

| 키 | 기본값 | 설명 |
|----|--------|------|
| `DATABASE_URL` | `sqlite:///./timesaving.db` | DB 연결 URL |
| `SECRET_KEY` | (변경 필요) | 세션 쿠키 서명 키 |
| `CORS_ORIGINS` | `http://localhost:5173` | 허용 오리진 |
| `ALGORITHM_TIMEOUT_SECONDS` | `120` | 알고리즘 최대 실행 시간(초) |

> 강의 300분반 이상 규모에서는 120초로 부족할 수 있습니다. 이때 작업 상태는
> `INFEASIBLE`이 아니라 **`TIMEOUT`** 으로 반환되며, 값을 300초 이상으로 올리면 해결됩니다.
> 규모별 실측치는 `PROJECT_CONTEXT.md` §6 참고.

## 도메인 규칙 요약

자세한 내용은 루트의 `PROJECT_CONTEXT.md`를 참고하세요. 특히 아래 세 가지는 필수입니다.

1. **제약 조건은 `Course`가 단독 소유합니다.** `Professor`에는 제약 필드가 없습니다.
2. **`non_preferred_days/periods`는 "비선호"가 아니라 "불가"(하드 제약)** 입니다. — HC-03/HC-04
3. **0교시는 온라인 전용**이라 강의실을 점유하지 않습니다. 강의별 `online_hours`(0–3)만큼
   0교시에 배정되고, `Assignment.room_id`는 NULL이 됩니다.

## 스키마 변경 시 주의

이 프로젝트에는 Alembic이 없고 `Base.metadata.create_all()`은 **기존 테이블을 변경하지 않습니다.**
모델을 바꿨다면 `init_db.py`의 `migrate()`에 이관 코드를 **멱등하게** 추가해야 기존 DB가 깨지지 않습니다.
