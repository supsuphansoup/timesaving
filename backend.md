# BE_REQUIREMENTS_CONTRACT

# 동서대학교 강의실 시간표 배정 시스템 - 백엔드 API 명세서 (BE_REQUIREMENTS_CONTRACT.md) v2.0 (완성본)

## 1. 개요 및 API 통신 규약 (API Contract)

### 1.1 프론트엔드-백엔드 연동 원칙

본 시스템은 프론트엔드(React)와 백엔드(FastAPI)가 분리된 환경에서 동작합니다. 프론트엔드 연동을 위해 다음의 **API 계약(API Contract)**을 엄격히 준수합니다.

- **Base URL**: `/api/v1`
- **네이밍 컨벤션**: 모든 API 요청(Request Body/Query) 및 응답(Response JSON)의 속성명은 **`snake_case`**를 준수합니다.
- **공통 응답 포맷 (Response Wrapper)**:
    
    ```json
    {
      "success": true,
      "status_code": 200,
      "message": "SUCCESS",
      "data": { ... }
    }
    ```
    
- **에러 응답 포맷**:
    
    ```json
    {
      "success": false,
      "status_code": 400,
      "error_code": "ER-07",
      "message": "필수 입력 항목이 누락되었습니다."
    }
    ```
    

---

## 2. 통합 에러 코드 명세 (Error Codes)

| HTTP 상태 | Error Code | 오류 상황 및 메시지 (Message) | 시스템 처리 / 비고 |
| --- | --- | --- | --- |
| `409` | **ER-01** | 교수 시간 충돌이 발생했습니다. | 시간표 생성/수정 검증 시 반환 |
| `409` | **ER-02** | 강의실 중복 배정이 발생했습니다. | 시간표 수정 검증 시 반환 |
| `409` | **ER-03** | 강의실 수용 인원이 부족합니다. | 수강 인원 > 수용 인원 시 차단 |
| `409` | **ER-04** | 사용 가능한 컴퓨터실이 없습니다. | 컴퓨터 필수 강의 배정 불가 시 반환 |
| `422` | **ER-05** | 제약조건을 모두 만족하는 시간표 생성 불가 | Infeasible 상태. 하드 제약조건 완화 안내 |
| `401` | **ER-06** | 권한이 없습니다. 로그인이 필요합니다. | 세션 만료 및 미인증 접근 시 |
| `400` | **ER-07** | 필수 입력 항목이 누락되었습니다. | Request Body 유효성 검사 실패 시 |
| `409` | **ER-08** | 중복된 데이터가 존재합니다. | 교수/강의실 중복 등록 방지 |
| `500` | **ER-09** | 일시적인 시스템 오류가 발생했습니다. | 서버 크래시, DB 연결 에러 등 |
| `504` | **ER-10** | 작업 시간이 초과되었습니다. | 생성 알고리즘 타임아웃 |
| `409` | **ER-11** | 다른 사용자가 이미 이 시간표를 수정했습니다. | Optimistic Locking 충돌 에러 |

---

## 3. 핵심 API 인터페이스 명세 (JSON Contract)

### 3.1 인증 (Authentication)

- **조교 로그인**: `POST /api/v1/auth/login`
    - `body`: `{"username": str, "password": str}`
    - `response`: 세션 쿠키 발급. `data` 영역 비어있음.
- **로그아웃**: `POST /api/v1/auth/logout`
    - `response`: 세션 쿠키 삭제.
- **비밀번호 변경**: `PUT /api/v1/auth/password`
    - `body`: `{"old_password": str, "new_password": str}`

### 3.2 기준 데이터 관리 (Master Data CRUD)

> ⚠️ **`semester_id`는 더 이상 사용하지 않습니다.** 학기 단위 분리를 걷어내고 전역 관리로
> 리팩토링되었습니다. 목록 조회에 `?semester_id=`를 붙일 필요가 없습니다.

**[교수 정보 관리]**
* **목록 조회**: `GET /api/v1/professors`
* **등록/수정**: `POST /api/v1/professors` / `PUT /api/v1/professors/{id}`
* `body`:
```json
{ "name": "홍길동", "employee_number": "60063", "department": "컴퓨터공학전공" }
```
> ⚠️ **교수에는 제약 조건 필드가 없습니다.** 불가/선호 요일·교시는 전부 `Course`가 소유합니다.
> (같은 교수라도 과목·분반마다 사정이 다르기 때문 — PROJECT_CONTEXT.md Rule 1)

**[강의실 정보 관리]**
* **목록 조회**: `GET /api/v1/rooms`
* **등록/수정**: `POST /api/v1/rooms` / `PUT /api/v1/rooms/{id}`
* `body`:
```json
{ "room_name": "601", "location": "U-IT관", "capacity": 51,
  "is_computer_room": false, "is_common_room": false, "remarks": "프로젝터 노후화" }
```

**[강의 정보 관리]**
* **목록 조회**: `GET /api/v1/courses`
* **등록/수정**: `POST /api/v1/courses` / `PUT /api/v1/courses/{id}`
* **전체 초기화**: `DELETE /api/v1/courses/action/reset`
* `body`:
```json
{
  "course_name": "자료구조", "professor_id": 10,
  "department": "컴퓨터공학전공", "target_grade": 2,
  "class_section": "101",
  "weekly_hours": 3,
  "online_hours": 1,
  "expected_students": 45, "requires_computer": true,

  "non_preferred_days": ["MON"], "non_preferred_periods": [1, 2],
  "preferred_days": ["TUE", "THU"], "preferred_periods": [3, 4],
  "fixed_room_ids": [], "unavailable_room_ids": [],
  "target_cohorts": ["컴퓨터공학전공_2"]
}
```
| 필드 | 의미 |
|---|---|
| `class_section` | 분반. 학부 관례상 `"101"`, `"102"` 형식 |
| `online_hours` | 온라인 시수 (0–3, 기본 0). **0교시에 강의실 없이 배정**됩니다 |
| `non_preferred_days` / `non_preferred_periods` | 이름과 달리 **하드 제약(불가)** — HC-03/HC-04 |
| `preferred_days` / `preferred_periods` | 소프트 제약(선호) — SC-01/SC-02 |

### 3.3 시간표 자동 생성 (Algorithm Engine)

- **시간표 자동 생성 요청**: `POST /api/v1/timetables/generate`
    - `body`: `{"min_candidates": 3}`  ← **`num_candidates` 아님**
    - `response (202 Accepted)`: `{"data": {"task_id": "uuid-..."}}`
- **비동기 작업 상태 Polling**: `GET /api/v1/timetables/tasks/{task_id}`

| status | 의미 |
|---|---|
| `PROCESSING` | 계산 중 |
| `COMPLETED` | 후보 생성 완료 |
| `INFEASIBLE` | 제약조건상 시간표가 **존재하지 않음**(증명됨) |
| `TIMEOUT` | 해가 있을 수 있으나 **제한 시간 초과** |
| `FAILED` | 예기치 못한 오류 |

> ⚠️ `INFEASIBLE`과 `TIMEOUT`을 같은 메시지로 묶지 마세요. 전자는 제약을 고쳐야 하고,
> 후자는 `ALGORITHM_TIMEOUT_SECONDS`를 늘려야 합니다. 응답의 `message`에 구체적 사유가 담깁니다.

- **추천안(후보) 리스트 조회**: `GET /api/v1/timetables/candidates`
    - `response`: 총점(`score`), 선호도 반영률(`pref_rate`), 쾌적도(`fitness_rate`), 충돌 수(`conflict_count`)

### 3.4 시간표 수정 및 재배정

- **수동 변경 검증 (실시간)**: `POST /api/v1/timetables/validate-move`
    - `body`: `{"assignment_id": int, "target_room_id": int | null, "target_day": str, "target_period": int}`
    - `response`: 충돌 시 아래 오류 코드 반환

| 코드 | 위반 |
|---|---|
| ER-01 | HC-02 교수 시간 중복 |
| ER-02 | HC-01 강의실 시간 중복 |
| ER-03 | HC-08 수용 인원 초과 |
| ER-04 | HC-07 컴퓨터실 필요 |
| ER-05 | HC-10 코호트(동일 수강 대상) 충돌 |
| ER-06 | 배정 불가 공동 시간대(`BLOCKED_SLOTS`) |
| ER-07 / ER-08 | HC-03 불가 요일 / HC-04 불가 교시 |
| ER-09 / ER-10 | HC-05 고정 강의실 / HC-06 배정 불가 강의실 |
| ER-11 | 0교시(온라인 전용)에 강의실을 지정함 |
| ER-12 | 대면 수업(1–9교시)에 강의실이 없음 |

- **수동 편집 / 스왑 / 잠금**: `POST /api/v1/timetables/manual-edit`, `/swap`, `/toggle-lock/{assignment_id}`
- **부분 재배정 (Partial Reassign)**: `POST /api/v1/timetables/reassign`
    - `body`: `{"fixed_assignment_ids": [1, 2, 3]}` — 잠근 배정은 유지한 채 나머지만 재생성
- **시간표 임시 저장 (Draft & Optimistic Locking)**: `POST /api/v1/timetables/{id}/draft`
    - `body`: `{"version": 1, "assignments": [...]}`
- **시간표 최종 확정**: `POST /api/v1/timetables/{id}/confirm`  ← **`/confirm/{id}` 아님**

### 3.5 조회 및 출력

- **조건별 시간표 조회**: `GET /api/v1/timetables/views`
    - `query`: `?type={room|professor|grade|department}&target_name={name}`
- **파일 내보내기 (PDF/Excel)**: `GET /api/v1/timetables/{id}/export`
    - `query`: `?format={pdf|excel}`
    - `excel`은 학부 배포 양식(이론실/실습실/교수님별/학과별 다중 시트, 연강 병합)으로 출력됩니다.
      상세 규격은 `PROJECT_CONTEXT.md` §7 참고.

### 3.6 이력 및 로그 관리

- **로그 목록 조회**: `GET /api/v1/logs`
    - `query`: `?log_type={LOGIN|GENERATE|MODIFY}`
    - `response`: 타임스탬프, 사용자(조교), 이벤트 타입, 상세 변경 내역(JSON) 반환.

---

## 4. 백엔드 보안 및 서버 설정 가이드 (NFRs)

1. **CORS 설정**: 프론트엔드 개발 및 운영 도메인에 대해 CORS를 명시적으로 허용해야 하며, Credentials(쿠키 전송)를 `true`로 설정해야 합니다.
2. **세션 기반 인증 보안**:
    - 조교의 로그인 세션 쿠키는 `httponly=True`, `secure=True`(HTTPS), `samesite="Lax"` 옵션을 반드시 적용하여 XSS 및 CSRF 공격을 방어합니다.
    - 비밀번호는 평문으로 저장하지 않고 `bcrypt` 등을 이용해 단방향 암호화하여 DB에 저장합니다.
3. **알고리즘 격리**: 시간표 생성 알고리즘(Python OR-Tools)은 CPU 집약적 작업이므로 FastAPI의 메인 Event Loop를 블로킹하지 않도록 `Celery`나 `BackgroundTasks`를 통해 워커(Worker) 프로세스에서 실행되어야 합니다.