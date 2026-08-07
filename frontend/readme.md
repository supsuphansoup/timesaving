# 동서대학교 강의실 시간표 배정 시스템 — Frontend

조교가 강의·교수·강의실 정보를 입력하고, 시간표를 자동 생성해 비교·수정·확정하는 관리자 웹 UI입니다.

## 기술스택

| 역할 | 기술 |
|------|------|
| 프레임워크 | React 18 + TypeScript |
| 빌드 | Vite 5 |
| 스타일 | Tailwind CSS 3 |
| HTTP | axios (JWT 인터셉터) |
| 아이콘 | lucide-react |
| 내보내기 | xlsx, jspdf, html2canvas |

## 빠른 시작

```bash
npm install
npm run dev
```

기본 포트는 `http://localhost:5173`이며, 백엔드(`http://localhost:8001`)가 함께 떠 있어야 합니다.

```bash
npm run build      # 타입 검사(tsc) + 프로덕션 빌드
npm run lint
```

## 화면 구성 (`src/pages/`)

| 페이지 | 역할 |
|---|---|
| `LoginPage` | 로그인. 토큰은 `localStorage`에 보관하고 새로고침 시 `GET /auth/me`로 세션 복구 |
| `DashboardPage` | 현황 요약 |
| `CoursesPage` | **강의 등록/수정** — 시수, 온라인 시수, 분반, 불가/선호 요일·교시 등 제약 입력 |
| `ProfessorsPage` | 교수 관리 (제약 조건 없음 — 제약은 강의가 소유) |
| `RoomsPage` | 강의실 관리 (정원, 컴퓨터실 여부) |
| `ComparePage` | **추천안 비교 · 수동 편집 · 부분 재배정 · 최종 확정** |
| `TimetableViewPage` | 강의실/교수/학년별 시간표 조회 |
| `LogsPage` | 이력 로그 |

## 입력 시 알아둘 도메인 규칙

- **불가 요일 / 불가 교시는 하드 제약입니다.** "비선호"가 아니라 **절대 배정되지 않습니다.**
  넓게 지정하면 생성이 실패할 수 있고, 그 사유가 화면에 그대로 표시됩니다.
- **온라인 수업 시수**(0–3시간, 기본 "없음")를 지정하면 그만큼 **0교시(08:00)에 강의실 없이**
  배정됩니다. 1~9교시가 강의실을 쓰는 대면 수업입니다.
- **분반**은 학부 관례에 따라 `101`, `102` 형식으로 입력합니다. 엑셀 출력에
  `과목명_분반_교수명` 형태로 그대로 노출됩니다.

## 생성 작업 상태 처리

`POST /timetables/generate` → `GET /timetables/tasks/{task_id}` 폴링 구조입니다.

| status | 처리 |
|---|---|
| `PROCESSING` | 폴링 계속 |
| `COMPLETED` | 후보 목록 갱신 |
| `INFEASIBLE` | 제약조건상 불가능 — 사유 표시 후 제약 수정 유도 |
| `TIMEOUT` | 시간 초과 — 사유 표시 후 제한 시간 상향 유도 |
| `FAILED` | 오류 표시 |

> ⚠️ 폴링 종료 조건에서 `TIMEOUT`을 빠뜨리면 화면이 무한 로딩에 걸립니다.
> `INFEASIBLE`과 `TIMEOUT`은 원인이 다르므로 같은 메시지로 묶지 마세요.

## API 계약 주의점

프론트-백엔드 필드명이 어긋나도 **요청은 200으로 통과하고 기본값이 조용히 쓰이므로** 발견이 매우 어렵습니다.
`src/types/index.ts`를 백엔드 Pydantic 스키마와 1:1로 유지하세요.

- 생성 요청 필드는 **`min_candidates`** (`num_candidates` 아님)
- 확정 엔드포인트는 **`POST /timetables/{id}/confirm`** (`/timetables/confirm/{id}` 아님)

전체 아키텍처와 알고리즘 명세는 루트의 `PROJECT_CONTEXT.md`를 참고하세요.
