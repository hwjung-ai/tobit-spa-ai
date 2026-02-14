# Screen Editor 상용화 준비도 감사 보고서

**작성일**: 2026-02-14
**범위**: Screen Editor + AI Copilot 기능
**목적**: Production 전환 전 비판적 검토

---

## 📊 Executive Summary

| 항목 | 준비도 | 주요 리스크 | 판정 |
|------|--------|------------|------|
| **에디터 코어** | 🟢 양호 | - | ✅ 운영 가능 |
| **Action 시스템** | 🟢 양호 | - | ✅ 운영 가능 |
| **스키마/검증** | 🟢 양호 | - | ✅ 운영 가능 |
| **AI Copilot** | 🔴 부족 | LLM 연동 없음 | ❌ 구현 필요 |
| **PropertiesPanel** | 🟡 중간 | 1,587줄 비대화 | 🟡 리팩터링 권장 |

---

## 1️⃣ 모듈 구조 분석

### 📁 파일 구조

```
apps/web/src/components/admin/screen-editor/
├── CopilotPanel.tsx          (201줄) - AI Copilot UI
├── ScreenEditor.tsx          (603줄) - 메인 에디터
├── ScreenEditorHeader.tsx    (272줄) - 헤더
├── ScreenEditorTabs.tsx      (489줄) - 탭 관리
├── actions/
│   ├── ActionEditorModal.tsx (752줄) - 액션 편집
│   ├── ActionTab.tsx         (447줄) - 액션 탭
│   └── PayloadTemplateEditor.tsx (213줄)
├── binding/
│   └── BindingTab.tsx        (217줄)
├── visual/
│   ├── PropertiesPanel.tsx   (1,587줄) 🔴 비대화
│   ├── CanvasComponent.tsx   (297줄)
│   ├── ComponentTreeView.tsx (183줄)
│   ├── GridCanvas.tsx        (248줄)
│   ├── VisualEditor.tsx      (166줄)
│   └── BindingEditor.tsx     (146줄)
├── preview/
│   └── PreviewTab.tsx        (310줄)
├── templates/
│   └── TemplateGallery.tsx   (291줄)
├── publish/
│   └── PublishGateModal.tsx  (252줄)
├── diff/
│   └── DiffViewer.tsx        (146줄)
└── common/
    └── PathPicker.tsx        (260줄)

총 7,906줄
```

### 📁 라이브러리 구조

```
apps/web/src/lib/ui-screen/
├── editor-state.ts           (55,436줄) 🔴 매우 큼
├── screen-templates.ts       (16,554줄)
├── screen-diff-utils.ts      (11,707줄)
├── binding-path-utils.ts     (12,524줄)
├── validation-utils.ts       (16,855줄)
├── component-registry.ts     (6,679줄)
├── binding-engine.ts         (7,193줄)
├── stream-binding.ts         (9,344줄)
├── expression-parser.ts      (10,185줄)
├── safe-functions.ts         (9,495줄)
└── ...
```

---

## 2️⃣ 기능 분석: 현재 화면 구현 가능 여부

### ✅ 지원하는 기능

| 기능 | 구현 상태 | 위치 |
|------|----------|------|
| **팝업/모달** | ✅ 완전 지원 | `ComponentType.modal`, modal 컴포넌트 |
| **액션 정의** | ✅ 완전 지원 | `ScreenAction`, `ComponentActionRef` |
| **API 연동** | ✅ 완전 지원 | API Manager 통합, `useActionCatalog` |
| **이벤트 체인** | ✅ 완전 지원 | `continue_on_error`, `retry_count`, `on_error_action_indexes` |
| **바인딩** | ✅ 완전 지원 | `{{state.xxx}}`, `{{context.xxx}}` |
| **조건부 표시** | ✅ 완전 지원 | `visibility.rule` |
| **테이블** | ✅ 완전 지원 | `TableComponent` |
| **차트** | ✅ 완전 지원 | `ComponentType.chart` |
| **탭** | ✅ 완전 지원 | `ComponentType.tabs` |
| **폼** | ✅ 완전 지원 | `ComponentType.form` |

### 📋 액션 시스템 상세

**ScreenAction (화면 레벨)**:
```typescript
interface ScreenAction {
  id: string;
  handler: string;           // /ops/ui-actions로 라우팅
  payload_template?: Record<string, unknown>;
  context_required?: string[];
}
```

**ComponentActionRef (컴포넌트 레벨)**:
```typescript
interface ComponentActionRef {
  id: string;
  handler: string;
  payload_template?: Record<string, unknown>;
  continue_on_error?: boolean;
  stop_on_error?: boolean;
  retry_count?: number;          // 0~5
  retry_delay_ms?: number;
  run_if?: string;               // 조건부 실행
  on_error_action_index?: number;
  on_error_action_indexes?: number[];  // 폴백 체인
}
```

### 🔴 제한사항

1. **복잡한 레이아웃**: 중첩 grid/modal 구조는 수동 JSON 편집 필요
2. **커스텀 컴포넌트**: 확장 포인트가 미구현
3. **계산된 표현식**: 문서화만 있고 구현 없음

---

## 3️⃣ AI Copilot 분석

### 🔴 Critical: LLM 연동 미구현

**현재 상태**:
```tsx
// CopilotPanel.tsx
const handleGenerateProposal = () => {
  if (!inputValue.trim()) return;
  
  const payload = {
    ...contextPayload,
    prompt: inputValue.trim(),
  };
  
  // ❌ 실제 LLM 호출 없음 - 단순히 context를 JSON으로 표시만 함
  setPatchText(JSON.stringify({ patch: [], context: payload }, null, 2));
};
```

**문제점**:
1. "Generate Proposal" 버튼이 실제로는 아무것도 생성하지 않음
2. 사용자가 직접 JSON Patch를 입력해야 함
3. AI가 자연어를 JSON Patch로 변환하는 기능 없음

### 🎯 필요 구현 사항

```typescript
// 권장 구현: 실제 LLM 연동
const handleGenerateProposal = async () => {
  if (!inputValue.trim()) return;
  
  setIsGenerating(true);
  
  try {
    // 1. 화면 스키마 + 프롬프트를 LLM으로 전송
    const response = await fetch("/api/ai/screen-copilot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        screen_schema: currentScreenSchema,
        prompt: inputValue.trim(),
        selected_component: selectedComponentId,
      }),
    });
    
    // 2. LLM이 JSON Patch 반환
    const { patch } = await response.json();
    
    // 3. Preview에 표시
    setPatchText(JSON.stringify(patch, null, 2));
  } catch (error) {
    setError(error.message);
  } finally {
    setIsGenerating(false);
  }
};
```

### 📋 AI Copilot 로드맵

| 단계 | 작업 | 예상 소요 |
|------|------|----------|
| **P0** | 백엔드 API `/api/ai/screen-copilot` 구현 | 2일 |
| **P0** | 프롬프트 템플릿 설계 (ScreenSchema → JSON Patch) | 1일 |
| **P1** | 컴포넌트 추천 기능 | 2일 |
| **P1** | 자연어 → 바인딩 표현식 변환 | 1일 |
| **P2** | 대화형 에디터 (chat interface) | 3일 |

---

## 4️⃣ 비판적 검토

### 🔴 R1. AI Copilot 미작동

**심각도**: Critical  
**현황**: UI는 있지만 실제 AI 기능 없음  
**영향**: 사용자 경험 저하, "AI 지원"이라는 기능 약속 불이행  
**조치**: 즉시 LLM 연동 구현 필요

### 🟡 R2. PropertiesPanel 비대화

**심각도**: Medium  
**현황**: 1,587줄 단일 파일  
**영향**: 유지보수 어려움, 변경 충돌  
**권장**:
```
PropertiesPanel/
├── index.tsx
├── TextProperties.tsx
├── TableProperties.tsx
├── ChartProperties.tsx
├── ModalProperties.tsx
└── CommonProperties.tsx
```

### 🟡 R3. editor-state.ts 과도한 크기

**심각도**: Medium  
**현황**: 55,436줄 (생성된 파일일 가능성)  
**확인 필요**: 실제 코드인지 생성된 타입인지 확인

### ✅ R4. 액션 시스템 잘 설계됨

- API Manager 통합
- Chain Policy (retry, fallback)
- 테스트 기능
- 스키마 기반 검증

### ✅ R5. 스키마 잘 정의됨

- `ScreenSchemaV1` 명확한 계약
- TypeScript + JSON Schema 이중 검증
- 확장 포인트 문서화

---

## 5️⃣ 현재 화면 구현 가능성 평가

### 📊 질문: "현재 내 각 화면을 이 에디터로 만들 수 있나?"

**답변**: 🟡 **부분 가능**

| 화면 유형 | 구현 가능성 | 비고 |
|----------|-----------|------|
| **단순 CRUD 폼** | ✅ 완전 가능 | 템플릿 있음 |
| **테이블 + 필터** | ✅ 완전 가능 | 바인딩 지원 |
| **모달 팝업** | ✅ 완전 가능 | modal 컴포넌트 |
| **탭 레이아웃** | ✅ 완전 가능 | tabs 컴포넌트 |
| **대시보드** | ✅ 완전 가능 | chart 컴포넌트 |
| **복잡한 중첩 구조** | 🟡 JSON 수동 편집 | 비주얼 에디터 한계 |
| **동적 컴포넌트** | ❌ 미지원 | 확장 포인트 미구현 |
| **AI 자동 생성** | ❌ 미지원 | LLM 연동 필요 |

### 권장사항

1. **단순 화면**: Screen Editor로 직접 구현
2. **복잡한 화면**: JSON 직접 편집 + Preview로 검증
3. **AI 지원**: 구현 후 사용

---

## 6️⃣ 운영 적용 체크리스트

### Pre-Launch (반드시 완료)

- [ ] AI Copilot LLM 연동 구현
- [ ] PropertiesPanel 리팩터링 (선택)
- [ ] 복잡한 화면 템플릿 추가
- [ ] 사용자 가이드 작성

### Day 1

- [ ] 에디터 성능 모니터링
- [ ] JSON Patch 에러율 추적
- [ ] 액션 실행 성공률 대시보드

### Week 1

- [ ] 사용자 피드백 수집
- [ ] 자주 쓰는 컴포넌트 패턴 분석
- [ ] AI Copilot 프롬프트 튜닝

---

## 7️⃣ 최종 판정

### 운영 적용 가능 여부: **🟡 조건부 승인**

| 기능 | 판정 | 조건 |
|------|------|------|
| **에디터 본체** | ✅ 승인 | 모니터링 필수 |
| **액션 시스템** | ✅ 승인 | - |
| **AI Copilot** | ❌ 보류 | LLM 연동 구현 후 |

### 권장 로드맵

1. **Phase 1 (즉시)**: AI Copilot 기능 제외하고 에디터만 운영
2. **Phase 2 (1주 후)**: AI Copilot LLM 연동 구현
3. **Phase 3 (2주 후)**: PropertiesPanel 리팩터링

---

## 💡 결론

**에디터 기능**: 현재 화면(팝업, 액션 등)을 **대부분 구현 가능**  
**AI Copilot**: **미구현 상태** - LLM 연동 작업 필요 (최소 3일)

**최종 권장**: AI Copilot 구현 완료 후 전체 기능 운영 권장

---

**감사 완료**: Screen Editor + AI Copilot 분석 완료
**최종 판정**: 조건부 운영 승인 (AI 제외 시 즉시 가능)