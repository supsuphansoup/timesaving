# 🚀 AI Nexus: 대학 강의 시간표 자동생성 시스템 (Timesaving) — Master AI Context

> **용도**: 새로운 AI 대화 세션 시작 시 본 문서를 첨부하면, AI가 프로젝트 전체 아키텍처, 데이터 모델, 최신 변경점, UI 로직, OR-Tools CP-SAT 솔버 명세 및 테스트/검증 파이프라인을 100% 파악하고 즉시 작업을 이어갈 수 있습니다.

---

## 1. 🌐 시스템 환경 및 기술 스택 (Environment & Tech Stack)

- **OS Environment**: Windows 10/11 (PowerShell / CMD)
- **Backend**: Python 3.11.9 (`venv` 가상환경), **FastAPI**, SQLAlchemy ORM, Uvicorn
- **Database**: SQLite (`backend/timesaving.db`) — WAL 모드 지원
- **Algorithm Engine**: **Google OR-Tools** (`cp_model.CpModel`, `cp_model.CpSolver` 기반 CP-SAT 스케줄링 솔버)
- **Frontend / UI**: HTML5 / Vanilla CSS / Vanilla JavaScript (`test/index.html` 기반 관리자용 전체 기능 대시보드 SPA UI)
- **주요 서버 실행 및 제어 명령어**:
  ```powershell
  # 가상환경 활성화 (필요 시)
  .\venv\Scripts\activate

  # 백엔드 서버 실행 (기본 포트: 8001)
  .\venv\Scripts\uvicorn.exe app.main:app --port 8001 --reload

  # 8001 포트 충돌 시 프로세스 종료 명령어 (Windows)
  taskkill /F /IM uvicorn.exe /T
  ```

---

## 2. 🏛️ 최근 아키텍처 및 도메인 모델 핵심 변경사항 (CRITICAL ARCHITECTURAL RULES)

### ⚠️ Rule 1. 제약 조건 속성은 'Professor'가 아닌 'Course' 모델이 단독 소유합니다.
- **기존 아키텍처의 문제**: 교수가 여러 강의나 반(A반, B반)을 맡을 때 개별 강의마다 불가/선호 요일과 교시를 다르게 설정할 수 없었습니다.
- **최신 리팩토링 결과**:
  - **`Professor` 모델**: 이름, 소속 학과, 이메일 등의 기본 교수 정보만 유지합니다. (제약 조건 관련 컬럼 없음)
  - **`Course` 모델**: 강의별 독립적인 제약 조건을 모두 포함합니다.
    - `weekly_hours` (int): 주당 시수 (예: 3, 4)
    - `expected_students` (int): 예상 수강 인원
    - `requires_computer` (bool): PC 실습실 필수 여부
    - `unavailable_days` (str): 불가 요일 (예: `"MON,WED"`)
    - `preferred_days` (str): 선호 요일 (예: `"TUE,THU"`)
    - `unavailable_periods` (str): 불가 교시 (예: `"1,2"`)
    - `preferred_periods` (str): 선호 교시 (예: `"3,4,5"`)
    - `fixed_room_ids` / `unavailable_room_ids`: 특정 강의실 고정 / 배정 불가 ID

### ⚠️ Rule 2. API 정합성 및 시간표 뷰 조회 구조
- `/api/v1/timetables/views?semester_id={id}&type={type}` (type: `room`, `professor`, `grade`, `department`):
  - DB 내에 상태가 **`CONFIRMED`**(최종 확정)된 시간표들의 배정 슬롯(`Assignment`)을 반환합니다.
  - 다중 후보 중 특정 단건 시간표를 테스트/검증할 경우, 과거의 `CONFIRMED` 시간표 데이터와 합산되지 않도록 DB 초기화 또는 `a["timetable_id"] == target_id` 필터링을 수행해야 합니다.

---

## 3. 📂 프로젝트 전체 소스코드 지도 (Codebase Architecture Map)

```
timesaving/
├── PROJECT_CONTEXT.md              # [현재 파일] AI 전용 마스터 온보딩 가이드
├── PROGRESS_REPORT.md              # 사용자/관리자용 진행사항 및 성과 보고서
└── backend/                        # 백엔드 및 전체 애플리케이션 루트
    ├── venv/                       # Python 가상환경
    ├── timesaving.db               # SQLite 데이터베이스 파일
    ├── app/
    │   ├── main.py                 # FastAPI 앱 엔트리포인트, CORS, 라우터 및 정적 파일 마운트
    │   ├── config.py               # Settings 및 전역 설정
    │   ├── models/                 # SQLAlchemy DB 모델
    │   │   ├── course.py           # [중요] 강의 모델 (모든 제약 조건 속성 보유)
    │   │   ├── professor.py        # 교수 모델
    │   │   ├── room.py             # 강의실 모델 (capacity, is_computer_room 등)
    │   │   ├── timetable.py        # Timetable(후보/확정) 및 Assignment(배정 슬롯)
    │   │   └── ...                 # user, semester, log 등
    │   ├── routers/                # REST API 엔드포인트
    │   │   ├── auth.py             # /api/v1/auth/login, /api/v1/auth/me (JWT 세션 복원)
    │   │   ├── courses.py          # 강의 및 제약 조건 CRUD API
    │   │   ├── timetables.py       # 시간표 자동 생성 요청, 후보 목록, select/confirm, 뷰 조회
    │   │   └── ...
    │   ├── services/
    │   │   └── timetable_service.py # [중요] OR-Tools 비동기 작업 큐, 상태 트래킹, 뷰 필터링
    │   └── algorithm/
    │       └── engine.py           # [핵심] Google OR-Tools CP-SAT 시간표 최적화 엔진
    └── test/
        ├── index.html              # [전체 화면 UI] 관리자 대시보드 (Pill 체크박스, 세션 유지)
        └── seed_and_verify.py      # [검증 자동화] 현실적 임의 데이터 시딩 및 알고리즘 100% 무위반 검증
```

---

## 4. 🧠 OR-Tools CP-SAT 최적화 엔진 명세 (`app/algorithm/engine.py`)

시간표 자동 생성 엔진은 Hard Constraint(하드 제약: 위반 불가)와 Soft Constraint(소프트 제약: 목적함수 최적화 가중치)로 분리되어 완벽하게 동작합니다.

### 1) Hard Constraints (절대 준수 하드 제약)
- **`HC-01 (Room Conflict)`**: 동일 시간·동일 강의실에 최대 1개 과목만 배정 (`add_at_most_one`)
- **`HC-02 (Professor Conflict)`**: 동일 시간에 동일 교수는 최대 1개 과목만 배정 (`add_at_most_one`)
- **`HC-05 (Computer Room Requirement)`**: `requires_computer=True`인 실습 강의는 반드시 `is_computer_room=True`인 강의실만 탐색
- **`HC-06 (Room Capacity)`**: `expected_students <= room.capacity` 만족 강의실만 탐색
- **`HC-07 (Unavailable Days / Periods)`**: `unavailable_days`, `unavailable_periods`에 지정된 요일/교시는 변수 생성 단계에서 제외하여 절대 회피
- **`HC-09 [신설] (Daily Max Hours Limit)`**: 과목당 하루에 최대 3시간 이하(`sum(day_vars) <= 3`)로만 배정되도록 제한하여, 4시간 이상 과목의 하루 몰림 방지 및 연강/분산 배치 균형 보장

### 2) Soft Constraints (목적 함수 가중치 최적화 - `model.maximize`)
- **선호 요일 (`preferred_days`)**: 배정 성공 시 슬롯당 **`+15점`** 보너스 부여
- **선호 교시 (`preferred_periods`)**: 배정 성공 시 슬롯당 **`+10점`** 보너스 부여

---

## 5. 🎨 프론트엔드 UI/UX 핵심 작동 로직 (`test/index.html`)

### 1) Pill Group 체크박스 다중 선택 인터페이스
- 텍스트 입력 방식을 완전히 없애고, 요일(`월,화,수,목,금`) 및 교시(`1~9교시`)를 둥근 Pill 스타일 태그 체크박스로 시각화했습니다.
- 백엔드에 전송하거나 조회할 때 자바스크립트가 배열을 CSV 문자열(예: `"MON,WED"`, `"1,2,3"`)로 정합성 있게 상호 변환합니다.

### 2) 새로고침 시 로그인 세션 영구 보존 (`checkSession`)
- 웹에서 새로고침(F5) 시 로그아웃되는 문제를 방지하기 위해, 페이지 렌더링 시 `localStorage.getItem("token")`을 읽어 `GET /api/v1/auth/me`를 자동 호출합니다.
- 토큰이 유효하면 사용자 프로필(username, role 등)과 화면 상태를 즉시 복구하여 끊김 없는 세션을 제공합니다.

---

## 6. 🧪 알고리즘 성능 검증 스크립트 및 벤치마크 (`test/seed_and_verify.py`)

### 1) 실행 방법
터미널에서 아래 명령어를 실행하면, DB를 초기화하고 임의 교수 6명, 강의실 6개, 제약조건이 설정된 12과목을 생성한 뒤 자동생성 알고리즘을 수행하고 정밀 검증을 출력합니다.

```powershell
cd backend
.\venv\Scripts\python.exe test\seed_and_verify.py
```

### 2) 최신 검증 벤치마크 결과 (Verified Performance)
- **하드 제약 조건 위반 건수**: **`0건` (100% 무위반 달성)**
  - PC 실습실 배정, 강의실 수용인원, 교수/시간 중복, 불가 요일/교시 회피 전 항목 100% 통과
- **소프트 제약 조건 달성률**:
  - **선호 요일 배정 적중률**: **`97.3%`**
  - **선호 교시 배정 적중률**: **`100.0%`**
- **과목별 주당 시수 및 일일 분산 배치 충족률**: **`100.0%`**
  - 예) 3시간 과목: 2일 분산(2시간 연강+1시간) 또는 3시간 연강
  - 예) 4시간 과목: 일일 최대 3시간 제한(HC-09)에 의해 2일 이상 분산 배치 완료

---

## 7. 🤖 새로운 AI 에이전트를 위한 작업 체크리스트 & 행동 수칙

1. **신규 제약 조건이나 기능 추가 시**:
   - DB 모델 변경 시 항상 `Course` 중심의 제약 구조를 따르세요. (`Professor` 모델에 제약 필드를 추가하지 마세요.)
2. **알고리즘 엔진(`engine.py`) 수정 시**:
   - 하드 제약은 위반 시 후보 자체가 생성되지 않아야 하므로 `model.add_at_most_one` 또는 `add_linear_constraint`로 강제하세요.
   - 선호도 가중치를 변경할 때는 요일 선호 가중치가 교시 선호 가중치보다 다소 높아야 실제 학사 관리자 선호도와 부합합니다.
3. **UI(`test/index.html`) 확장 시**:
   - 새로운 과목 설정이 추가되면 기존의 **Pill Group 체크박스 스타일** 및 **디자인 시스템(Glassmorphism, 다크모드 대응)** 일관성을 반드시 유지하세요.
   - 새로고침 시 로그인 정보가 증발하지 않도록 기존 `checkSession()` 로직 및 `auth/me` 연동 규칙을 훼손하지 마세요.
