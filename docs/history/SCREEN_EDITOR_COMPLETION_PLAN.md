# Screen Editor 완성 작업계획서

**작성일**: 2026-02-14
**목표**: Screen Editor 상용화 완료
**예상 소요**: 3일

---

## 📋 작업 범위

| 항목 | 우선순위 | 예상 소요 | 담당 |
|------|----------|----------|------|
| AI Copilot 백엔드 API | P0 | 4시간 | - |
| AI Copilot 프론트엔드 연동 | P0 | 3시간 | - |
| 프롬프트 템플릿 설계 | P0 | 2시간 | - |
| 테스트 코드 작성 | P1 | 2시간 | - |
| 문서 업데이트 | P1 | 1시간 | - |

---

## 1️⃣ Phase 1: 백엔드 API 구현

### 1.1 API 엔드포인트

```
POST /api/ai/screen-copilot
```

**요청**:
```json
{
  "screen_schema": { ... },      // 현재 화면 스키마
  "prompt": "버튼을 파란색으로 바꿔줘",
  "selected_component": "btn_submit",
  "context": {
    "available_handlers": ["api_manager.execute", "navigate"],
    "state_paths": ["state.user", "state.items"]
  }
}
```

**응답**:
```json
{
  "patch": [
    { "op": "replace", "path": "/components/0/props/color", "value": "blue" }
  ],
  "explanation": "버튼 색상을 파란색으로 변경했습니다.",
  "confidence": 0.95
}
```

### 1.2 구현 위치

- `apps/api/app/modules/ai/screen_copilot/`
  - `router.py` - API 엔드포인트
  - `service.py` - LLM 호출 로직
  - `schemas.py` - 요청/응답 스키마
  - `prompts.py` - 프롬프트 템플릿

---

## 2️⃣ Phase 2: 프론트엔드 연동

### 2.1 수정 파일

- `apps/web/src/components/admin/screen-editor/CopilotPanel.tsx`
  - `handleGenerateProposal()` 함수 수정
  - 로딩 상태, 에러 처리 추가
  - 백엔드 API 호출

### 2.2 추가 기능

- 로딩 스피너
- 에러 토스트
- 설명 표시 (AI가 변경사항 설명)
- 신뢰도 표시 (선택)

---

## 3️⃣ Phase 3: 프롬프트 템플릿

### 3.1 시스템 프롬프트 구조

```
You are a Screen Editor AI Copilot. Your task is to generate JSON Patch operations
to modify screen schemas based on user requests.

## Screen Schema
{screen_schema}

## Available Components
- text, markdown, button, input, form, table, chart, badge, tabs, accordion, modal, keyvalue, divider, row, column

## Available Handlers
{available_handlers}

## State Paths
{state_paths}

## Selected Component
{selected_component}

## User Request
{prompt}

## Response Format
Return a JSON object with:
1. "patch": Array of JSON Patch operations (RFC6902)
2. "explanation": Brief explanation of changes
3. "confidence": Float between 0-1

Example response:
{
  "patch": [
    {"op": "replace", "path": "/components/0/props/label", "value": "New Label"}
  ],
  "explanation": "Updated button label",
  "confidence": 0.9
}
```

---

## 4️⃣ 진행 상황

- [x] Phase 1: 백엔드 API 구현 ✅
  - [x] 라우터 생성 (`apps/api/app/modules/ai/router.py`)
  - [x] 서비스 로직 구현 (`apps/api/app/modules/ai/service.py`)
  - [x] 스키마 정의 (`apps/api/app/modules/ai/schemas.py`)
  - [x] 프롬프트 템플릿 (`apps/api/app/modules/ai/prompts.py`)
  - [x] 메인 앱 라우터 등록 (`apps/api/main.py`)
- [x] Phase 2: 프론트엔드 연동 ✅
  - [x] API 호출 로직
  - [x] 로딩/에러 처리
  - [x] UI 개선 (신뢰도 표시, 설명 표시)
- [ ] Phase 3: 테스트
  - [ ] 단위 테스트
  - [ ] 통합 테스트
- [ ] Phase 4: 문서 업데이트

---

## 5️⃣ 구현 완료 내역

### 백엔드 API

**엔드포인트**: `POST /ai/screen-copilot`

**파일 구조**:
```
apps/api/app/modules/ai/
├── __init__.py     # 모듈 초기화
├── schemas.py      # 요청/응답 스키마
├── prompts.py      # LLM 프롬프트 템플릿
├── service.py      # LLM 호출 서비스
└── router.py       # FastAPI 라우터
```

**기능**:
- 화면 스키마 + 자연어 프롬프트 → JSON Patch 생성
- LLM 호출 로깅 (tb_llm_call_log)
- Patch 검증
- 신뢰도 점수 반환

### 프론트엔드

**파일**: `apps/web/src/components/admin/screen-editor/CopilotPanel.tsx`

**기능**:
- "Generate with AI" 버튼 → 백엔드 API 호출
- 로딩 스피너 표시
- AI 설명 표시
- 신뢰도 프로그레스 바
- 제안 사항 목록

---

**완료일**: 2026-02-14
**상태**: 백엔드/프론트엔드 구현 완료, 테스트/문서 진행 예정
