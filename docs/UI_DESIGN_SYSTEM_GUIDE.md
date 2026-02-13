# UI Design System Guide (Final)

> Project: tobit-spa-ai
> Scope: `apps/web` UI 전반
> Framework: Next.js 16 + React 19 + Tailwind CSS v4 + shadcn/ui
> Last Updated: 2026-02-13

---

## 1. 목적과 적용 범위

이 문서는 `apps/web`의 **공통 UI 품질 기준**과 **구현 규칙**을 정의하는 정본입니다.

상세 구현 예시(복붙 가능한 스니펫)는 `docs/UI_PATTERN_RECIPES.md`를 사용합니다.

적용 범위:
- 페이지 레이아웃, 공통 컴포넌트, 타이포그래피, 컬러, 간격, 상호작용
- 라이트/다크 모드, 접근성, 상태 표현(로딩/빈 상태/에러)
- 코드 리뷰 시 UI 일관성 검증 기준

비적용 범위:
- 기능별 비즈니스 로직
- 작업 이력(Phase 로그) 나열
- 장문 코드 레시피 (별도 문서로 분리)

원칙: 이 문서는 "규칙"만 유지합니다. 대규모 변경 이력은 Git 커밋/PR 설명으로 관리합니다.

---

## 2. 소스 오브 트루스

UI 기준값은 아래 파일을 기준으로 합니다.

- CSS 토큰/유틸리티: `apps/web/src/app/globals.css`
- TS 토큰 헬퍼: `apps/web/src/lib/design-tokens.ts`
- 공용 유틸: `apps/web/src/lib/utils.ts` (`cn`)
- 실전 패턴 레시피: `docs/UI_PATTERN_RECIPES.md`

규칙:
- 문서와 구현이 다르면, 우선 구현(`globals.css`)을 확인 후 문서를 즉시 동기화합니다.
- 새 토큰/유틸을 추가하면 본 문서도 같은 커밋에서 업데이트합니다.

---

## 3. 핵심 규칙

### 3.1 반드시 지킬 것 (MUST)

- 색상은 **의미 기반(semantic)** 클래스 사용:
  - `text-foreground`, `text-muted-foreground`
  - `bg-surface-base`, `bg-surface-elevated`, `bg-surface-overlay`
  - `border-variant`
- 조건부 class 병합은 항상 `cn()` 사용
- 모든 인터랙티브 요소는 `focus-visible` 상태 제공
- 라이트/다크 모드 모두에서 가독성과 대비 보장
- 상수화 가능한 스타일은 유틸리티 클래스로 승격

### 3.2 피해야 할 것 (MUST NOT)

- 하드코딩 팔레트 남용: `text-slate-*`, `bg-slate-*`, `border-slate-*`의 직접 반복 사용
- 임의값 남용: `tracking-[0.27em]`, `text-[11px]`, `rounded-[7px]` 등
- 정적 스타일을 `style={{ ... }}`로 반복 작성
- 템플릿 리터럴 className 결합

### 3.3 제한적 허용 (ALLOWED)

- `style={{ ... }}`는 동적 계산이 필요한 경우에만 허용:
  - 좌표/크기 계산, 캔버스/그래프 라이브러리 인터페이스, 런타임 위치값
- 서드파티 라이브러리(AG Grid, Monaco, Recharts, React Flow)의 전용 스타일 API 사용

---

## 4. 디자인 토큰 기준

### 4.1 Surface / Text / Border

기본적으로 아래 의미 체계를 사용합니다.

| 의미 | 클래스 |
|---|---|
| 기본 배경 | `bg-surface-base` |
| 상승된 배경 | `bg-surface-elevated` |
| 오버레이 배경 | `bg-surface-overlay` |
| 기본 텍스트 | `text-foreground` |
| 보조 텍스트 | `text-muted-foreground` |
| 표준 경계선 | `border-variant` |

### 4.2 상태 색상

| 상태 | 클래스 (예시) |
|---|---|
| Primary | `bg-sky-600 hover:bg-sky-500` |
| Success | `bg-emerald-600` 또는 `bg-green-600` |
| Warning | `bg-amber-600` 또는 `bg-yellow-600` |
| Error/Destructive | `bg-rose-600` 또는 `bg-red-600` |

규칙:
- 상태 색상은 의미와 매칭되어야 하며, 같은 의미에 다른 색을 혼용하지 않습니다.

### 4.3 불투명도 표현

Tailwind opacity modifier를 사용합니다.

예시:
- `bg-sky-500/34`
- `bg-slate-950/60`
- `border-emerald-500/50`

---

## 5. 타이포그래피

### 5.1 텍스트 스케일

| 용도 | 클래스 |
|---|---|
| Tiny 라벨 | `text-tiny` (또는 `text-[10px]` 금지, `text-tiny` 우선) |
| 보조 텍스트 | `text-xs`, `text-sm` |
| 본문 | `text-base` |
| 섹션 타이틀 | `text-lg` |
| 페이지 타이틀 | `text-2xl` |

### 5.2 대문자 라벨 규칙

- 대문자 텍스트는 `tracking-wider`를 표준으로 사용
- `tracking-[0.xem]` 임의값 사용 금지

---

## 6. 간격, 반경, 그림자, 레이어

### 6.1 간격 스케일

기본 간격:
- `gap-2` (8px)
- `gap-3` (12px)
- `gap-4` (16px)
- `gap-6` (24px)

권장 패딩:
- 카드: `p-4`
- 섹션: `p-5`
- 대형 패널: `p-6`

### 6.2 반경 스케일

| 클래스 | 용도 |
|---|---|
| `.br-badge` | 배지/필 |
| `.br-btn` | 버튼/인풋 |
| `.br-card` | 카드 |
| `.br-section` | 섹션 |
| `.br-panel` | 대형 패널 |

### 6.3 그림자 스케일

- `shadow-sm`: 기본 컨테이너
- `shadow-md`: 팝업/중간 강조
- `shadow-lg`: 플로팅 UI
- `shadow-2xl`: 강한 강조 다이얼로그

임의 그림자(`shadow-[...]`)는 지양합니다.

### 6.4 Z-Index 스케일

- `z-10`: sticky
- `z-20`: dropdown/tooltip
- `z-30`: modal
- `z-40`: toast/alert
- `z-50`: 전역 최상위 오버레이

---

## 7. 표준 레이아웃 패턴

### 7.1 페이지 기본 래퍼

```tsx
<div className="min-h-screen bg-surface-base text-foreground">
  <main className="w-full px-4 pb-16 pt-4 md:px-6 md:pb-4">...</main>
</div>
```

### 7.2 섹션/카드/패널

- 섹션: `.container-section`
- 카드: `.container-card`
- 패널: `.container-panel`

직접 클래스로 작성할 때도 위 클래스와 동일한 토큰 조합을 유지합니다.

### 7.3 ADMIN 페이지

ADMIN 페이지는 아래 순서를 기본으로 합니다.

1. 페이지 헤더 (`title + description + actions`)
2. 컨트롤 바(필터/검색/액션)
3. 본문 섹션(테이블/폼/그래프)

표준 헤더는 `PageHeader` 계열 컴포넌트를 우선 사용합니다.

---

## 8. 컴포넌트 구현 규칙

### 8.1 버튼

- Primary: `btn-primary` 또는 동등한 primary 토큰
- Secondary/Ghost/Destructive는 의미에 맞는 변형 사용
- hover/disabled/focus-visible 상태 누락 금지

### 8.2 입력 컴포넌트

- 기본 입력: `.input-container`
- 텍스트 영역/셀렉트도 동일한 border, radius, focus ring 체계 유지

### 8.3 코드 블록

- 일반: `.code-block`
- 대형: `.code-block-lg`

### 8.4 테이블

- 헤더/행 경계선은 `border-variant` 기준
- 헤더 텍스트는 보조 톤 + 가독성 높은 굵기
- hover 상태는 surface 계열로 통일

### 8.5 빈 상태 / 로딩 상태

- 빈 상태: 다음 행동(CTA) 포함
- 로딩 상태: 스피너/스켈레톤 + 의미 있는 문구 제공

### 8.6 리사이즈 핸들 (Split View)

표준 클래스:
- 컨테이너: `.resize-handle-col`
- 그립: `.resize-handle-grip`
- 활성 상태: `.is-active`

규칙:
- 폭은 `w-2` 기준
- 페이지별 개별 hover 로직/시각 스타일 재정의 금지
- 접근성 속성(`role="separator"`, `aria-orientation`) 제공

### 8.7 탭 vs 선택 (중요)

- `탭(Tab)`: 동일 페이지 내 **동등한 뷰/섹션 전환**
  - 예: `Definition / Logic / Test`, `JSON Editor / Form Builder / Test / Logs`
  - 공통 클래스: `nav-tab*`, `panel-tab*`, `panel-tab-trigger`
- `선택(Selection)`: 현재 컨텍스트에서 **값/타입 선택**
  - 예: `metric / event / schedule / anomaly`
  - 공통 클래스: `choice-chip*`

규칙:
- 같은 역할의 UI는 페이지가 달라도 동일한 클래스 체계를 사용
- hover/active 상태에서 대비(텍스트 가독성)가 깨지면 안 됨
- 탭 활성 상태에서 글자 크기/두께가 갑자기 바뀌지 않도록 고정

---

## 9. 다크 모드 규칙

- 색상은 항상 라이트/다크 쌍으로 설계합니다.
- 다크 전용 하드코딩(`bg-slate-950` 단독 등) 금지
- `globals.css` 변수 기반 클래스 사용을 우선합니다.

예시:

```tsx
<div className="bg-surface-base text-foreground border border-variant" />
```

---

## 10. 접근성 규칙

- 키보드 포커스 가시성 필수 (`focus-visible`)
- 클릭 가능한 비버튼 요소 사용 시 키보드 동작 보장
- 아이콘 전용 버튼은 `aria-label` 필수
- 상태 변경은 텍스트/아이콘/색상 중 2개 이상으로 전달 권장

---

## 11. 코드 스타일 규칙

- `className` 결합은 `cn()`만 사용
- 조건부 스타일은 class 토큰 조합으로 해결
- 주석은 "왜 필요한지" 중심으로 최소화
- 재사용 가능한 패턴은 공용 클래스/컴포넌트로 승격

예시:

```tsx
import { cn } from "@/lib/utils";

<div className={cn("container-section", isActive && "border-variant")} />
```

---

## 12. 금지/안티패턴

- 매직 넘버 스타일 (`p-[13px]`, `text-[11px]`, `rounded-[7px]`)
- 랜덤 색상/Hex 하드코딩 남발
- 제목/본문/보조 텍스트의 계층 구분 부재
- 동일 의미 상태를 화면마다 다른 색으로 표현
- 라이트/다크 대비 부족으로 인한 가독성 저하

---

## 13. 리뷰 체크리스트

PR 리뷰 시 아래를 확인합니다.

- [ ] 색상이 semantic 클래스 기반인가
- [ ] `cn()` 사용 규칙을 지켰는가
- [ ] 다크 모드에서 동일 정보가 읽히는가
- [ ] 포커스/키보드 접근성이 보장되는가
- [ ] 임의값/인라인 정적 스타일이 없는가
- [ ] 컨테이너/입력/버튼 패턴이 표준 클래스와 일치하는가
- [ ] 빈 상태/로딩 상태가 사용자 행동을 안내하는가

---

## 14. 마이그레이션 가이드

기존 화면 정비 순서:

1. 하드코딩 색상 제거
2. semantic 클래스 치환
3. 대문자 라벨 `tracking-wider` 통일
4. 컨테이너/인풋/버튼 표준 클래스 적용
5. 인라인 정적 스타일 제거
6. 다크 모드/접근성 검증

치환 우선순위 예시:
- `border-slate-*` -> `border-variant`
- `bg-white`, `bg-slate-*` -> `bg-surface-*`
- `text-slate-*` -> `text-foreground`/`text-muted-foreground`

---

## 16. JSON Screen System Standards

`UIScreenRenderer`를 통해 JSON 정의만으로 화면을 구성할 때도 동일한 디자인 표준이 적용됩니다. 에이전트나 개발자가 새로운 `.screen.json`을 작성할 때 반드시 다음 매핑 규칙을 준수해야 합니다.

### 16.1 타이포그래피 매핑

JSON의 `fontSize`와 `fontWeight` props는 가이드의 텍스트 스케일과 다음과 같이 매핑됩니다:

| JSON Prop | CSS 클래스 (토큰) | 용도 |
|---|---|---|
| `fontSize: "xs"` | `text-xs` | 보조 텍스트, 설명 |
| `fontSize: "sm"` | `text-sm` | 일반 본문, 폼 라벨 |
| `fontSize: "base"` | `text-base` | 강조 본문 |
| `fontSize: "lg"` | `text-lg` | 카드/섹션 타이틀 |
| `fontSize: "2xl"` | `text-2xl` | 페이지 대제목 |
| `fontWeight: "semibold"` | `font-semibold` | 강조/헤더 |

### 16.2 컬러 및 상태 매핑

JSON 내에서 하드코딩된 HEX/RGB 색상 사용을 지양하고, 컴포넌트의 `variant` 또는 `conditional_styles`를 사용하여 의미론적으로 접근합니다.

- **Badge (`badge`)**:
  - `variant: "success"` (Emerald 기반)
  - `variant: "warning"` (Amber 기반)
  - `variant: "danger"` (Rose 기반)
  - `variant: "outline"` (Border variant 기반)
- **Table/Chart 조건부 스타일**:
  - `color: "#ef4444"` 대신 가능한 경우 `variant`를 지원하는 컴포넌트를 우선 사용하거나, 런타임이 지원하는 토큰 키워드를 사용합니다.

### 16.3 레이아웃 및 간격

- **Spacing**: `gap` 속성은 4px 배수를 사용합니다 (`gap: 4` -> 16px).
- **Layout Type**:
  - `type: "stack"`: 기본 수직/수평 나열
  - `type: "grid"`: 대시보드 및 복합 레이아웃
  - `type: "form"`: 폼 중심 세로 레이아웃
  - `type: "list"`: 목록형 레이아웃
  - `type: "modal"`: 중앙 오버레이 레이아웃
  - `type: "dashboard"`: 절대 위치 기반 대시보드 레이아웃
- **Container**: JSON 컴포넌트들은 내부적으로 `.container-card`, `.container-section` 표준 클래스를 사용하여 렌더링되도록 설계되어 있습니다.

### 16.4 JSON 작성 체크리스트

- [ ] `fontWeight: "semibold"`가 필요한 헤더에 적용되었는가
- [ ] `fontSize`가 본 문서의 텍스트 스케일 범위를 벗어나지 않는가 (`text-tiny` ~ `text-2xl`)
- [ ] 하드코딩된 특정 색상 코드 대신 표준 `variant`를 사용했는가
- [ ] `row`, `column` 컴포넌트의 `gap`이 일관되게 적용되었는가

---

## 17. 참고 문서

- `AGENTS.md`
- `docs/FEATURES.md`
- `docs/TESTING_STRUCTURE.md`
- `docs/UI_PATTERN_RECIPES.md` (JSON 스니펫 포함)
- `apps/web/src/app/globals.css`
- `apps/web/src/lib/design-tokens.ts`
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Radix UI Primitives](https://www.radix-ui.com/primitives)
- [Nielsen Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)
