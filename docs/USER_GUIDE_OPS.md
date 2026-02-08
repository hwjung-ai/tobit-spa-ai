# OPS User Guide

**Last Updated**: 2026-02-08

## 1. 목적과 대상

이 문서는 현재 코드 기준 OPS 운영 흐름을 따라할 수 있게 정리한 실습형 가이드다.

대상 사용자:
- OPS 운영자
- 플랫폼/백엔드 엔지니어
- 장애 분석 담당자(Inspector/Regression/RCA)

---

## 2. 현재 OPS 구조 요약

### 2.1 질의 실행 경로

- `POST /ops/query`: 단일 모드 실행
- `POST /ops/ask`: 전체 오케스트레이션 모드 실행
- `POST /ops/ci/ask`: rerun/replan 기반 재실행

프론트 모드와 백엔드 모드 매핑:

| UI 모드 (`/ops`) | 백엔드 모드 | 엔드포인트 |
|---|---|---|
| `all` (전체) | orchestration | `POST /ops/ask` |
| `ci` (구성) | `config` | `POST /ops/query` |
| `metric` (수치) | `metric` | `POST /ops/query` |
| `history` (이력) | `hist` | `POST /ops/query` |
| `relation` (연결) | `graph` | `POST /ops/query` |
| `document` (문서) | `document` | `POST /ops/query` |

### 2.2 파이프라인

`route_plan -> validate -> execute -> compose -> present`

핵심 포인트:
- `execute` 단계에서 Tool 호출이 발생한다.
- Tool 호출 결과는 trace/tool_calls/references로 남는다.
- `compose/present`에서 Answer Blocks로 변환된다.

### 2.3 Tools 개념 (중요)

현재 OPS는 Asset + Tool 중심 구조다.

- Asset: Prompt/Policy/Query/Mapping/Source/Resolver/Screen/Catalog/Tool
- Tool: 실행 단위(예: database_query, http_api, graph_query, python_script)
- Tool 라이프사이클: Draft -> Test -> Publish -> Trace 관측 -> 회귀 점검

관련 화면:
- `/admin/tools`: Tool 생성/필터/퍼블리시/테스트
- `/admin/catalogs`: DB 스키마 카탈로그 스캔/조회 (Tool SQL 정확도에 영향)
- `/admin/inspector`: trace에서 실제 tool_calls 확인

---

## 3. Admin 탭 정리 (현재 명칭 기준)

현재 Admin 탭:
- `Assets`, `Tools`, `Catalogs`, `Screens`, `Explorer`, `Settings`, `Inspector`, `Regression`, `Observability`, `Logs`

OPS와 직접 연관되는 탭:
- `Assets`: 플래너/정책/매핑/쿼리/소스/스크린 자산 관리
- `Tools`: 실행 Tool 자산 관리(생성/퍼블리시/테스트)
- `Catalogs`: 스키마 카탈로그 관리(툴 질의 정확도)
- `Inspector`: trace, stage 입출력, tool_calls, references 분석
- `Regression`: Golden Query 회귀 테스트
- `Observability`: OPS/CEP KPI 관측
- `Logs`: query history/execution trace/audit/file log 조회
- `Explorer`: 데이터 원천 조회(Postgres/Neo4j/Redis, read-only)

간접 연관 탭:
- `Screens`: OPS 응답의 UI Screen 자산 편집 시 연관
- `Settings`: 운영 파라미터/정책값 관리

---

## 4. 빠른 시작 튜토리얼

목표: 질문 실행 -> trace 분석 -> tool 조정 -> 회귀 확인까지 1회 완료.

### Step 1. OPS 질의 실행

1. `/ops` 접속
2. 모드 선택(`전체` 또는 `구성/수치/이력/연결/문서`)
3. 질문 입력 후 실행

검증 포인트:
- 응답 블록이 렌더링된다.
- Summary Strip에 route/tools/replan 정보가 표시된다.

### Step 2. Inspector에서 trace 확인

1. 결과 영역에서 Inspector 이동
2. `/admin/inspector?trace_id=...`에서 stage 출력 확인
3. `tool_calls`, `references`, `applied_assets` 확인

검증 포인트:
- 어떤 Tool이 호출됐는지 식별된다.
- 실패 시 어느 stage에서 깨졌는지 확인 가능하다.

### Step 3. Tool 조정

1. `/admin/tools` 이동
2. 문제 Tool 선택 후 설정/입력스키마 점검
3. 필요 시 Draft 수정 후 Test Panel로 검증
4. 검증 통과 시 Publish

검증 포인트:
- Tool Test가 성공한다.
- 재실행 시 동일 에러가 재발하지 않는다.

### Step 4. Catalog 확인 (SQL/DB Tool 사용 시)

1. `/admin/catalogs` 이동
2. source_ref와 table scan 상태 확인
3. 필요한 경우 scan 재실행

검증 포인트:
- 필요한 테이블/컬럼이 catalog에 반영된다.
- Tool이 잘못된 테이블명을 생성하지 않는다.

### Step 5. 재실행 및 회귀 확인

1. `/ops`에서 동일 질문 재실행
2. `/admin/regression`에서 Golden Query 등록/실행
3. 필요하면 `/ops/rca` 또는 RCA 패널로 차이 분석

검증 포인트:
- baseline 대비 품질 저하가 없다.
- 변경 이유를 trace diff로 설명할 수 있다.

---

## 5. 운영 시나리오별 플레이북

### 5.1 결과 정확도가 떨어짐

1. Inspector에서 `plan`과 `tool_calls` 확인
2. Assets에서 Prompt/Policy/Mapping 점검
3. Tools에서 입력 스키마/timeout/쿼리 구성 점검
4. Catalog 최신성 확인

### 5.2 응답이 느림

1. Inspector에서 stage별 지연 구간 확인
2. 느린 Tool 식별 후 Tool 설정/쿼리 최적화
3. Observability에서 추세 확인

### 5.3 문서 모드 품질 저하

1. 문서 인덱스/검색 로그 점검
2. question wording과 mode 분기 확인
3. 필요 시 all 모드와 document 모드 결과 비교

### 5.4 재계획(replan) 반복

1. trace의 `replan_events` 확인
2. trigger/patch 적용 내용 검토
3. resolver/policy/tool 파라미터를 보수적으로 재설정

---

## 6. OPS 관련 주요 API

질의/오케스트레이션:
- `POST /ops/query`
- `POST /ops/ask`
- `POST /ops/ci/ask`

UI Action/Screen 연계:
- `GET /ops/ui-actions/catalog`
- `POST /ops/ui-actions`
- `POST /ops/ui-editor/presence/heartbeat`
- `POST /ops/ui-editor/presence/leave`
- `GET /ops/ui-editor/presence/stream`

관측/회귀/RCA:
- `GET /ops/observability/kpis`
- `GET /ops/summary/stats`
- `GET /ops/golden-queries`
- `POST /ops/golden-queries`
- `POST /ops/golden-queries/{query_id}/run-regression`
- `GET /ops/regression-runs`
- `POST /ops/rca/analyze-trace`
- `POST /ops/rca/analyze-regression`
- `POST /ops/stage-compare`

---

## 7. 배포 전 체크리스트

- `/ops`에서 대표 질문 세트 실행 결과를 확인했다.
- `/admin/inspector`에서 핵심 trace의 tool_calls/references를 점검했다.
- Tool 수정이 있었으면 `/admin/tools` 테스트 후 publish했다.
- SQL/DB Tool이면 `/admin/catalogs` 스캔 상태를 확인했다.
- `/admin/regression`에서 baseline 대비 회귀가 없는지 확인했다.
- `/admin/observability`, `/admin/logs`에서 오류율/예외 로그를 확인했다.

---

## 8. 향후 고도화 과제

- Tool 실행 정책(재시도/timeout/fallback) 표준화
- Tool별 SLO 대시보드 및 알람 강화
- stage별 비용/latency budget 자동 제어
- 회귀 실패 시 자동 RCA 초안 생성 고도화
