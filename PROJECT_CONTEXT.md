# 🚀 AI Nexus: 대학 강의 시간표 자동생성 시스템 (Timesaving) — Master AI Context

> **용도**: 새로운 AI 대화 세션 시작 시 본 문서를 첨부하면, AI가 프로젝트 전체 아키텍처, 데이터 모델, 최신 변경점, UI 로직, OR-Tools CP-SAT 솔버 명세 및 테스트/검증 파이프라인을 100% 파악하고 즉시 작업을 이어갈 수 있습니다.

---

## 1. 🌐 시스템 환경 및 기술 스택 (Environment & Tech Stack)

- **OS Environment**: Windows 10/11 (PowerShell / CMD)
- **Backend**: Python 3.11.9 (`venv` 가상환경), **FastAPI**, SQLAlchemy ORM, Uvicorn
- **Database**: SQLite (`backend/timesaving.db`) — WAL 모드 지원
- **Algorithm Engine**: **Google OR-Tools 9.10** (`cp_model.CpModel`, `cp_model.CpSolver` 기반 CP-SAT 스케줄링 솔버)
- **Frontend / UI**: **React 18 + TypeScript + Vite + Tailwind CSS** (`frontend/`) — axios로 백엔드 REST API 호출
  - `backend/test/index.html`은 초기 개발용 단일 파일 대시보드로, **현재 주 UI가 아닙니다.**
- **주요 서버 실행 및 제어 명령어**:
  ```powershell
  # 가상환경 활성화 (필요 시)
  .\venv\Scripts\activate

  # 백엔드 서버 실행 (기본 포트: 8001)
  .\venv\Scripts\uvicorn.exe app.main:app --port 8001 --reload

  # 8001 포트 충돌 시 프로세스 종료 명령어 (Windows)
  taskkill /F /IM uvicorn.exe /T
  ```
  ```powershell
  # 프론트엔드 개발 서버 (기본 포트: 5173)
  cd frontend
  npm install
  npm run dev
  ```

---

## 2. 🏛️ 최근 아키텍처 및 도메인 모델 핵심 변경사항 (CRITICAL ARCHITECTURAL RULES)

### ⚠️ Rule 1. 제약 조건 속성은 'Professor'가 아닌 'Course' 모델이 단독 소유합니다.
- **기존 아키텍처의 문제**: 교수가 여러 강의나 반(A반, B반)을 맡을 때 개별 강의마다 불가/선호 요일과 교시를 다르게 설정할 수 없었습니다.
- **최신 리팩토링 결과**:
  - **`Professor` 모델**: 이름, 소속 학과, 이메일 등의 기본 교수 정보만 유지합니다. (제약 조건 관련 컬럼 없음)
  - **`Course` 모델**: 강의별 독립적인 제약 조건을 모두 포함합니다. (컬럼명·타입은 `backend/app/models/course.py` 기준)
    - `weekly_hours` (int): 주당 시수 (예: 3, 4)
    - `online_hours` (int, 0–3): **온라인(비대면) 시수.** 0이면 전부 대면. `weekly_hours` 이하만 허용
    - `expected_students` (int): 예상 수강 인원
    - `requires_computer` (bool): PC 실습실 필수 여부
    - `non_preferred_days` (JSON list): **불가 요일** — HC-03, 하드 제약 (예: `["MON", "WED"]`)
    - `non_preferred_periods` (JSON list): **불가 교시** — HC-04, 하드 제약 (예: `[1, 2]`)
    - `preferred_days` (JSON list): 선호 요일 — SC-01, 소프트 (예: `["TUE", "THU"]`)
    - `preferred_periods` (JSON list): 선호 교시 — SC-02, 소프트 (예: `[3, 4, 5]`)
    - `fixed_room_ids` / `unavailable_room_ids` (JSON list): 특정 강의실 고정(HC-05) / 배정 불가(HC-06)
    - `block_preference` (str): 연강/분산 블록 배정 방식 (예: `"3"`, `"2+1"`, `"1+1+1"`)
    - `target_cohorts` (JSON): 대상 학과 및 학년 코호트 (교양/전공 충돌 방지용, 비었으면 `"{department}_{target_grade}"`로 대체)
    - `fixed_schedules` (JSON): 특정 요일·교시 강제 고정 스케줄 (예: `[{"day": "TUE", "period": 0}]`)
    - `mutually_exclusive_with` (JSON): 동시간대 배정 절대 금지 과목명(부분 문자열) 목록

> ⚠️ **`non_preferred_*` 는 이름과 달리 "비선호"가 아니라 "불가(Hard)"입니다.** 요구사항 명세서 §6.3 HC-03/HC-04 및
> §6.5 "1. 불가 요일과 불가 교시를 먼저 제외한다"에 따라, 엔진은 이 슬롯의 **결정 변수를 아예 생성하지 않습니다.**
> 감점이 아니라 원천 배제이므로, 설정 범위가 너무 넓으면 `InfeasibleModelError`가 발생합니다.

### ⚠️ Rule 2. API 정합성 및 시간표 뷰 조회 구조
- `/api/v1/timetables/views?semester_id={id}&type={type}` (type: `room`, `professor`, `grade`, `department`):
  - DB 내에 상태가 **`CONFIRMED`**(최종 확정)된 시간표들의 배정 슬롯(`Assignment`)을 반환합니다.
  - 다중 후보 중 특정 단건 시간표를 테스트/검증할 경우, 과거의 `CONFIRMED` 시간표 데이터와 합산되지 않도록 DB 초기화 또는 `a["timetable_id"] == target_id` 필터링을 수행해야 합니다.

### ⚠️ Rule 3. 0교시는 온라인(비대면) 전용이며 강의실을 점유하지 않습니다.

- **0교시(08:00)** 는 온라인 수업만 배정됩니다. **1–9교시**가 강의실을 쓰는 대면 수업입니다.
- 강의별 `online_hours`(0–3)만큼이 0교시에 배정되고, 나머지 `weekly_hours - online_hours`가 대면으로 배정됩니다.
- 온라인 수업은 **하루 1시간씩, 서로 다른 요일의 0교시**에 들어갑니다.
- `Assignment.room_id`는 온라인 수업일 때 **NULL**입니다.

| 제약 | 0교시 적용 여부 |
|---|---|
| HC-01 강의실 중복 / HC-07 컴퓨터실 / HC-08 정원 | **미적용** (강의실을 쓰지 않음) |
| HC-02 교수 충돌 / HC-10 코호트 충돌 | **적용** (온라인이어도 교수는 한 명, 학생도 동시 수강 불가) |
| HC-11 연강 블록 | 대면(1–9교시)에만 적용 |

> 구현 방식: 엔진은 0교시에 **`x`(강의실 포함) 변수를 만들지 않고 `y`(점유) 변수만** 사용합니다.
> 모든 공유 제약이 `y` 기반이라 이 한 가지 변경으로 위 표가 전부 성립합니다.

---

## 3. 📂 프로젝트 전체 소스코드 지도 (Codebase Architecture Map)

```
timesaving/
├── PROJECT_CONTEXT.md              # [현재 파일] AI 전용 마스터 온보딩 가이드
├── PROGRESS_REPORT.md              # 사용자/관리자용 진행사항 및 성과 보고서
├── 요구사항 명세서 (공동작업) ....md  # [원본 스펙] FR/HC/SC/ER 정의의 최종 근거
├── backend/                        # FastAPI 백엔드
│   ├── venv/                       # Python 가상환경
│   ├── timesaving.db               # SQLite 데이터베이스 파일
│   ├── init_db.py                  # 테이블 생성 + 관리자 계정 + [중요] migrate() 스키마 이관
│   ├── app/
│   │   ├── main.py                 # FastAPI 앱 엔트리포인트, CORS, 라우터 및 정적 파일 마운트
│   │   ├── config.py               # Settings 및 전역 설정 (algorithm_timeout_seconds 등)
│   │   ├── models/                 # SQLAlchemy DB 모델
│   │   │   ├── course.py           # [중요] 강의 모델 (모든 제약 조건 속성 보유)
│   │   │   ├── professor.py        # 교수 모델 (제약 조건 없음 — Rule 1 참고)
│   │   │   ├── room.py             # 강의실 모델 (capacity, is_computer_room 등)
│   │   │   ├── timetable.py        # Timetable(후보/확정) 및 Assignment(배정 슬롯)
│   │   │   └── ...                 # user, semester, log 등
│   │   ├── routers/                # REST API 엔드포인트
│   │   │   ├── auth.py             # /api/v1/auth/login, /api/v1/auth/me (JWT 세션 복원)
│   │   │   ├── courses.py          # 강의 및 제약 조건 CRUD API
│   │   │   ├── timetables.py       # 자동 생성 요청, 후보 목록, 수동 편집/스왑, confirm, 뷰 조회
│   │   │   └── ...
│   │   ├── services/
│   │   │   ├── timetable_service.py # [중요] 비동기 작업 큐·상태 트래킹, validate_move(수동 편집 검증), 뷰 필터링
│   │   │   └── export_service.py    # [중요] 학부 양식 엑셀 출력(다중 시트 블록 격자) + PDF
│   │   └── algorithm/
│   │       ├── engine.py           # [핵심] OR-Tools CP-SAT 모델 구성 + 2-Phase solve()
│   │       ├── constraints.py      # [중요] 시간 상수·차단 슬롯·임계값 단일 정의처
│   │       └── scorer.py           # 후보 점수/선호도·쾌적도 반영률/충돌 수 산출 (engine의 W_* 재사용)
│   └── test/
│       ├── index.html              # 레거시 단일 파일 관리자 대시보드 (현재 주 UI 아님)
│       ├── seed_and_verify.py      # [검증 자동화] 임의 데이터 시딩 및 알고리즘 무위반 검증
│       └── seed_mock_data.py       # 목업 데이터 시딩
└── frontend/                       # [주 UI] React 18 + TypeScript + Vite + Tailwind
    └── src/
        ├── api/                    # axios 클라이언트 (JWT 인터셉터)
        ├── pages/                  # Login, Dashboard, Courses, Professors, Rooms,
        │                           #   Compare(추천안 비교/수동편집/부분재배정), TimetableView, Logs
        ├── components/             # Header, Sidebar, TimetableGrid, ErrorBoundary 등
        └── types/index.ts          # 백엔드 스키마와 1:1 대응되는 타입 정의
```

> ⚠️ **`app/solver/scheduler.py`와 `app/seed.py`는 삭제되었습니다.**
> `app/seed.py`는 어디서도 import되지 않으면서 삭제된 구 스키마(`semester_id`, `name`, `grade`,
> `computer_required`)를 사용해 실행하면 바로 깨지는 상태였습니다.
> `scheduler.py`는 어디에서도 import되지 않는 구버전 중복 솔버였고,
> 요일을 한글(`"월"`)로, 교시를 1~9로 다루어 현행 엔진(`"MON"`, 0~9)과 체계가 달라 혼동만 유발했습니다.
> 스케줄링 로직은 **`app/algorithm/` 하위가 유일한 진실의 원천(single source of truth)** 입니다.

---

## 4. 🧠 OR-Tools CP-SAT 최적화 엔진 명세 (`app/algorithm/engine.py`)

시간표 자동 생성 엔진은 Hard Constraint(하드 제약: 위반 불가)와 Soft Constraint(소프트 제약: 목적함수 최적화 가중치)로 분리되어 동작합니다.

- 시간 상수·차단 슬롯·임계값은 전부 **`app/algorithm/constraints.py`** 에 모여 있습니다.
  (`DAYS`, `PERIODS`=0~9교시, `BLOCKED_SLOTS`={수요일 5·6교시}, `LUNCH_PERIODS`={4,5},
  `MAX_DAILY_HOURS_PER_COURSE`=3, `MAX_DAILY_HOURS_PER_PROFESSOR`=4)
- 결정 변수는 `x[(course, day, period, room)]`(배정 여부)과 `y[(course, day, period)]`(강의실 무관 점유)의 2계층입니다.
- **1슬롯 = 1교시**입니다. `Assignment.duration`은 항상 1이며, 연강은 인접 슬롯이 연속 배정되어 표현됩니다.

### 1) Hard Constraints (절대 준수 하드 제약)

변수 생성 단계에서 아예 제외하는 것(①군)과 모델 제약으로 강제하는 것(②군)으로 나뉩니다.

**① 변수 생성 시 원천 배제 (요구사항 §6.5 적용 순서와 동일)**
- **`HC-03 (불가 요일)`**: `non_preferred_days`에 지정된 요일 제외
- **`HC-04 (불가 교시)`**: `non_preferred_periods`에 지정된 교시 제외
- **`HC-05 (고정 강의실)`**: `fixed_room_ids`가 있으면 해당 강의실만 후보로 유지
- **`HC-06 (배정 불가 강의실)`**: `unavailable_room_ids` 제거
- **`HC-07 (컴퓨터실)`**: `requires_computer=True`면 `is_computer_room=True`인 강의실만 유지
- **`HC-08 (수용 인원)`**: `room.capacity >= expected_students`인 강의실만 유지
- **`BLOCKED_SLOTS`**: 수요일 5·6교시(공동 시간) 제외
- **`ONLINE_PERIOD`(0교시)**: 대면 수업의 `x` 변수를 만들지 않음 (온라인 전용 — Rule 4 참고)

  → 위 필터 결과 배정 가능한 슬롯이 없으면 **`InfeasibleModelError`** 를 던져
  "어떤 강의가 왜 불가능한지" 사용자에게 그대로 전달합니다. (`TASK_INFEASIBLE`)

**② 모델 제약으로 강제**
- **`HC-01 (Room Conflict)`**: 동일 시간·동일 강의실에 최대 1개 과목 (`add_at_most_one`)
- **`HC-02 (Professor Conflict)`**: 동일 시간에 동일 교수는 최대 1개 과목 (`add_at_most_one`)
- **`HC-09 (Daily Max Hours)`**: 과목당 하루 최대 `MAX_DAILY_HOURS_PER_COURSE`(3)시간
- **`HC-10 (Cohort Conflict)`**: `target_cohorts`가 겹치는 과목끼리 동시간 배정 금지 — **하드 제약입니다** (수강 대상이 같은 학생이 두 수업을 동시에 들을 수 없으므로)
- **`HC-11 (Block Preference)`**: `block_preference`("3", "2+1", "1+1+1")로 연강 블록 개수 상한 지정. 미지정 시 `weekly_hours`로부터 유추
- **`HC-12 (Mutually Exclusive)`**: `mutually_exclusive_with` 지정 과목들 간의 동시 배정 금지
- **`HC-13 (Fixed Schedules)`**: 특정 요일/교시 강제 고정 (차단 시간대를 지정한 경우 경고 로그 후 무시)
- **주당 시수**: `sum(x[course]) == weekly_hours`

### 2) Soft Constraints (목적 함수 가중치 최적화)

가중치는 `engine.py`의 `W_*` 상수로 단일 정의되어 있고, **`scorer.py`가 이 상수를 그대로 import** 하므로
화면에 표시되는 점수와 CP-SAT가 실제로 최적화한 목적함수 값이 **정확히 일치**합니다.

| 항목 | 상수 | 가중치 |
|---|---|---|
| 선호 요일 (SC-01) | `W_PREFERRED_DAY` | **+15** / 슬롯 |
| 선호 교시 (SC-02) | `W_PREFERRED_PERIOD` | **+10** / 슬롯 |
| 점심시간(4·5교시) 회피 | `W_LUNCH` | **−5** / 슬롯 |
| 연강 보너스 | `W_CONSECUTIVE` | **+20** / 인접쌍 (`"1+1+1"` 과목은 제외) |
| 강의실 이동 (첫 강의실 초과분) | `W_EXTRA_ROOM` | **−10** / 추가 강의실 |
| 교수 일일 과부하 (4시간 초과분) | `W_PROF_OVERLOAD` | **−10** / 초과 시간 |
| 우주공강 (Idle Time) | `W_PROF_IDLE` | **−5** / 공강 교시 |

> 목적함수 변수 `obj_var`의 도메인은 하드코딩이 아니라 **소프트항의 실제 상·하한을 누적 계산**해 결정합니다.
> (도메인이 좁으면 정상 해가 조용히 INFEASIBLE로 잘려나가기 때문)

### 3) 2-Phase 알고리즘 엔진

모델 빌드는 비싼 연산이므로 **모델을 단 한 번만 생성**하고 두 단계가 같은 객체를 공유합니다.

- **Phase 1 (최적화)**: `model.maximize(obj_var)`로 최고 점수 해를 도출합니다. (예산의 50%)
- **Phase 2 (다양성 확보)**: `model.clear_objective()`로 목적함수를 제거해 **만족 문제(satisfaction)** 로 전환한 뒤,
  1. `obj_var >= best - tolerance` (tolerance = `max(50, |best| // 5)`) 로 품질 하한을 고정하고
  2. 직전 해에 대해 **no-good 절단** `sum(직전에 켜진 x) <= n - max(1, n//10)` 을 누적 추가합니다.

  즉 "풀고 나서 비슷하면 버리는" 방식이 아니라 **최소 10% 슬롯 차이를 제약으로 강제**하므로 후보의 상이성이 보장됩니다.
  `INFEASIBLE`이면 더 이상 다른 후보가 없다는 뜻이므로 즉시 종료하고, `UNKNOWN`(시간 초과)이면 다른 시드로 재시도합니다
  (`MAX_PHASE2_ATTEMPTS`=6). 요청 개수를 못 채우면 **가짜로 복제하지 않고 실제 후보 개수만 반환**합니다.

### 4) 수동 편집과의 정합성

`services/timetable_service.validate_move()`는 엔진의 하드 제약과 **동일한 규칙**을 검사해야 합니다.
현재 HC-01/02/03/04/05/06/07/08/10, `BLOCKED_SLOTS`, 그리고 0교시 온라인 규칙(ER-11/ER-12)을 모두 검증합니다.
**엔진에 하드 제약을 추가하면 반드시 `validate_move()`에도 같은 검사를 추가하세요.**
그렇지 않으면 자동 생성은 막는 배치를 드래그로는 만들 수 있는 불일치가 생깁니다.

---

## 5. 🎨 프론트엔드 UI/UX 핵심 작동 로직 (`frontend/src/`)

### 1) 요일·교시 다중 선택 (`CoursesPage.tsx`)
- 요일(`월,화,수,목,금`)과 교시(`0~9교시`)를 체크박스 그룹으로 입력받습니다.
- 화면에는 한글 요일(`월`)을, 백엔드에는 영문 코드(`MON`)를 보내며 `DAY_MAP` / `REV_DAY_MAP`으로 상호 변환합니다.
- 백엔드 필드는 **CSV 문자열이 아니라 JSON 배열**입니다 (`["MON","WED"]`, `[1,2,3]`).
- **"불가 요일/교시"는 하드 제약**이므로 라벨에 "※ 절대 배정되지 않습니다"를 명시합니다.
  넓게 지정하면 생성이 실패(`INFEASIBLE`)할 수 있고, 그 사유는 `/tasks/{id}` 응답의 `message`로 그대로 표시됩니다.
- **온라인 수업 시수** 드롭다운(0–3시간, 기본 "없음"). 주당 시수보다 큰 값은 옵션에서 제외되고,
  주당 시수를 줄이면 온라인 시수가 자동으로 따라 내려갑니다. (Rule 3 참고)

### 2) 생성 작업 상태 (`GET /timetables/tasks/{task_id}`)

| status | 의미 | 프론트 처리 |
|---|---|---|
| `PROCESSING` | 계산 중 | 폴링 계속 |
| `COMPLETED` | 후보 생성 완료 | 후보 목록 갱신 |
| `INFEASIBLE` | **제약조건상 시간표가 존재하지 않음** (증명됨) | 사유 표시 → 제약 수정 유도 |
| `TIMEOUT` | **해가 있을 수 있으나 제한 시간 초과** | 사유 표시 → 시간 늘리기 유도 |
| `FAILED` | 예기치 못한 오류 | 오류 표시 |

> ⚠️ `INFEASIBLE`과 `TIMEOUT`을 **절대 합치지 마세요.** 둘을 같은 메시지로 표시하면
> 멀쩡한 제약조건을 헛되이 뜯어고치게 됩니다. 엔진도 `InfeasibleModelError`와
> `SolverTimeoutError`를 구분해 던집니다.

### 3) 추천안 비교·수정 (`ComparePage.tsx`)
- `POST /timetables/generate` 는 **`min_candidates`** 필드를 받습니다. (`num_candidates` 아님 — 오타 시 조용히 기본값 3개로 동작)
- 확정 엔드포인트는 **`POST /timetables/{id}/confirm`** 입니다. (`/timetables/confirm/{id}` 아님 — 404)
- 잠금(`toggle-lock`)한 배정 ID를 `POST /timetables/reassign`의 `fixed_assignment_ids`로 넘기면
  해당 슬롯은 그대로 둔 채 나머지만 재배정됩니다.

### 4) 새로고침 시 로그인 세션 보존
- 페이지 렌더링 시 `localStorage`의 토큰을 읽어 `GET /api/v1/auth/me`를 자동 호출하고, 유효하면 사용자 프로필을 복구합니다.
- axios 인터셉터(`src/api/`)가 모든 요청에 `Authorization` 헤더를 주입합니다.

---

## 6. 🧪 알고리즘 성능 검증 스크립트 및 벤치마크 (`test/seed_and_verify.py`)

### 1) 실행 방법
터미널에서 아래 명령어를 실행하면, DB를 초기화하고 임의 교수 6명, 강의실 6개, 제약조건이 설정된 12과목을 생성한 뒤 자동생성 알고리즘을 수행하고 정밀 검증을 출력합니다.

```powershell
cd backend
.\venv\Scripts\python.exe test\seed_and_verify.py
```

### 3) 확장성 한계 (실측)

같은 조건에서 규모만 키워 측정한 결과입니다. **목표 규모에서는 충분하지만 무한히 확장되지는 않습니다.**

| 규모 | x 변수 | 결과 |
|---|---|---|
| 63분반 / 8강의실 **(컴퓨터공학부 실제 규모)** | 14,280 | ✅ 정상 |
| 130분반 / 16강의실 | 57,582 | ✅ 정상 |
| 320분반 / 40강의실 | 397,216 | ❌ 기본 120초로 실패 — **300초를 주면 풀림** |
| 600분반 / 70강의실 | 1,365,746 | ❌ 모델 생성에만 30초 |

**규명된 것**
- 실패 지점은 최적화가 아니라 **실행 가능한 해를 하나 찾는 단계**입니다.
- 목적함수를 완전히 꺼도 320분반은 동일하게 실패합니다 → **최적화 압력 탓이 아님**
- 강의실 후보를 줄여 변수를 397K→68K(5.8배)로 낮춰도 결과가 같습니다 → **변수 개수 탓도 아님**
- 320분반 기준 CP-SAT **presolve만 24초**를 쓰고, 이후 탐색에서 첫 해를 못 찾습니다.

**아직 규명되지 않은 것**: 130~320분반 사이 탐색 난이도가 급변하는 근본 원인.
확장 계획이 생기면 HC-11 블록 제약이나 교수 공강 reified 구조를 하나씩 끄며 실측해야 합니다.

> ⚠️ 규모가 커서 시간이 부족한 경우 상태는 **`TIMEOUT`** 이며 `INFEASIBLE`이 아닙니다.
> 실용적 완화책은 `ALGORITHM_TIMEOUT_SECONDS`를 300초 이상으로 올리는 것입니다.

---

## 7. 📤 엑셀 출력 명세 (`app/services/export_service.py`)

`GET /api/v1/timetables/{id}/export?format=excel`

출력물은 **학부에서 실제로 쓰는 배포 양식**과 같은 구조입니다.
(근거 파일: `2026-2_시간표_컴퓨터공학부.xlsx` — 11개 시트를 역설계했습니다)

### 1) 시트 구성은 데이터에서 생성합니다 — 하드코딩 금지

| 시트 | 생성 규칙 | 블록 단위 | 블록 제목 | 셀 표기 |
|---|---|---|---|---|
| 이론실 | `is_computer_room=False` | 강의실 | `001_60석` | `과목_분반_교수` |
| 실습실 | `is_computer_room=True` | 강의실 | `107_45석` | `과목_분반_교수` |
| 교수님별 | 배정된 교수 전원 | 교수 | `고관표
(60063)` | `과목_분반_강의실` |
| {학과}별 (N개) | `department` 고유값마다 1시트 | 학년 | `1학년` | `과목_분반_교수_강의실` |

> ⚠️ 학과 목록을 상수로 박지 마세요. 학기마다 학과·교수·강의실이 바뀌므로
> **코드 수정 없이 자동 대응되어야 합니다.**

### 2) 블록 격자 레이아웃

- 앵커 셀(블록 제목) 오른쪽에 `월화수목금`, 아래로 교시 행
- 블록 배치: **가로 7열 / 세로 11행 간격, 한 줄에 3블록** (`BLOCK_COL_STRIDE`, `BLOCK_ROW_STRIDE`, `BLOCKS_PER_ROW`)
- 교시 라벨: 강의실·학년 시트 `1 (09:00)` / 교수 시트 `1교시  9:00` (교시 p → `8+p`시)
- **연강은 셀 병합** — 같은 (과목, 요일, 강의실)의 연속 교시를 하나로 묶습니다
- `BLOCKED_SLOTS` 위치에 `비교과` 표기
- **강의실 시트에는 0교시 행이 없습니다** (온라인 전용 — Rule 3)
- 강의실 없는 온라인 수업은 `과목_분반_온라인`으로 표기

### 3) 주의점

- 학과별 블록은 **같은 슬롯에 두 과목이 올 수 있습니다**(코호트가 다른 경우).
  덮어쓰지 말고 줄바꿈으로 함께 표시해야 합니다.
- 출력 검증은 원본 파일 분석에 썼던 것과 **같은 프로브**(블록 탐지 → 교시·병합 확인)로 하면
  구조 일치를 객관적으로 확인할 수 있습니다.

---

## 8. 🤖 새로운 AI 에이전트를 위한 작업 체크리스트 & 행동 수칙

1. **신규 제약 조건이나 기능 추가 시**:
   - DB 모델 변경 시 항상 `Course` 중심의 제약 구조를 따르세요. (`Professor` 모델에 제약 필드를 추가하지 마세요.)
   - 제약의 Hard/Soft 판단은 **요구사항 명세서 §6.3/§6.4와 "제약조건 속성" 표(Hard/Soft 열)** 를 최종 근거로 삼으세요.
2. **알고리즘 엔진(`engine.py`) 수정 시**:
   - 하드 제약은 **가능하면 변수 생성 단계에서 제외**하세요 (모델이 작아지고 원인 진단 메시지를 줄 수 있습니다).
     슬롯 간 상호작용이 필요한 경우에만 `add_at_most_one` 등 모델 제약을 쓰세요.
   - **하드 제약을 추가하면 `timetable_service.validate_move()`에도 동일한 검사를 반드시 추가**하세요. (§4-4 참고)
   - **정수 변수 도메인을 하드코딩하지 마세요.** `span`/`idle`/`excess`/`obj_var`의 상한이 실제 최댓값보다 작으면
     정상 해가 조용히 `INFEASIBLE`로 잘려나갑니다. `len(PERIODS)`나 소프트항 누적 상·하한으로 산출하세요.
   - 소프트 가중치는 `engine.py`의 `W_*` 상수 한 곳에서만 정의합니다.
     `scorer.py`가 이 상수를 import하므로, **엔진에만 항을 추가하고 스코어러를 빠뜨리면 화면 점수와 실제 최적화 기준이 어긋납니다.**
   - 선호도 가중치를 변경할 때는 요일 선호 가중치가 교시 선호 가중치보다 다소 높아야 실제 학사 관리자 선호도와 부합합니다.
3. **UI(`frontend/`) 확장 시**:
   - Tailwind 유틸리티 클래스 기반의 기존 컴포넌트 스타일 일관성을 유지하세요.
   - `src/types/index.ts`의 타입은 백엔드 Pydantic 스키마와 1:1로 맞추세요.
     **필드명이 어긋나도 요청은 200으로 통과하고 기본값이 조용히 쓰이므로** 버그를 찾기 매우 어렵습니다.
   - 새로고침 시 로그인 정보가 증발하지 않도록 기존 `auth/me` 세션 복구 규칙을 훼손하지 마세요.
4. **DB 스키마를 바꿀 때는 `init_db.py`의 `migrate()`에 이관 코드를 반드시 추가하세요.**
   - 이 프로젝트에는 Alembic이 없고 `Base.metadata.create_all()`은 **기존 테이블을 절대 변경하지 않습니다.**
   - 컬럼 추가는 `ALTER TABLE ... ADD COLUMN`, SQLite에서 NOT NULL→NULL 같은 변경은 테이블 재생성이 필요합니다.
   - 반드시 **멱등**하게 작성하고(두 번 실행해도 안전), 구 스키마 DB로 실제 테스트하세요.
5. **엑셀 출력(§7) 변경 시**: 시트 구성을 상수로 박지 말고 데이터에서 파생시키세요.
6. **알고리즘 변경 후에는 반드시**:
   - 하드 제약 전수 감사(생성된 배정을 순회하며 HC-01~HC-13 위반 0건 확인)
   - `compute_score()` 결과 == CP-SAT `objective_value` 일치 확인
   - 후보들이 실제로 서로 다른지 확인 (동일 배정 집합이 중복 반환되면 안 됨)
   - 0교시에 강의실이 배정되지 않았는지 확인 (Rule 3)
