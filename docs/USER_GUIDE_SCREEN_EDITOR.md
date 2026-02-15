# Screen Editor User Guide

> **Last Updated**: 2026-02-15
> **Status**: ✅ **Production Ready**
> **Production Readiness**: 94%

## Recent Changes (2026-02-14 to 2026-02-15)

### ⭐ AI Copilot Feature (NEW - MAJOR FEATURE!)
- **What**: Natural language screen design assistance powered by LLM
- **Endpoint**: POST `/ai/screen-copilot`
- **Capabilities**:
  - Convert natural language commands to UI modifications
  - Confidence scoring (0.0-1.0) for each suggestion
  - 6 quick action buttons (Create, Move, Delete, Rename, Style, Layout)
  - One-click apply with undo support
- **Usage**: See new "3. AI Copilot Assistant" section below for complete guide

### 🎓 Onboarding System (NEW)
- **What**: 7-step interactive tutorial for first-time users
- **Features**: localStorage completion tracking, skip/complete buttons, contextual help
- **Steps**: Welcome → Components → Properties → Canvas → Quick Actions → Advanced → Complete
- **Auto-trigger**: Shown on first login or when clicking "?" help button

### 🏗️ Architecture Improvements
- **Production Readiness**: 85% → 94%
- **Copilot UI/UX**: Stabilized JSON parsing, error recovery, multi-candidate parsing
- **Onboarding System**: Full tutorial coverage with empty state guidance

---

## 문서의 성격

이 문서는 Screen Editor를 처음 사용하는 사용자가
빈 화면부터 시작해 실제 배포 가능한 Screen Asset을 완성하도록 돕는 튜토리얼이다.

핵심 목표:
1. 화면 구조를 직접 만든다.
2. bindings/actions를 연결해 동작 화면을 완성한다.
3. preview/publish/rollback까지 운영 흐름을 익힌다.
4. **AI Copilot을 활용해 화면 설계를 가속화한다** (NEW)
5. **Onboarding 시스템으로 기본 개념을 학습한다** (NEW)

---

## 0. 시작 전 준비

### 0.1 준비 체크

1. `/admin/screens` 접근 가능
2. 필요한 권한(편집/발행) 보유
3. 연결할 API 또는 `/ops/ui-actions` handler 준비

### 0.2 화면 구조 빠른 이해

- 목록: `/admin/screens`
- 편집기: `/admin/screens/{screen_id}`

편집 탭:
- Visual
- JSON
- Binding
- Action
- Preview
- Diff

#### 0.2.1 컴포넌트 타입 전체 레퍼런스 (15종)

시스템이 지원하는 모든 컴포넌트 타입과 용도를 아래 표로 정리한다.

| 타입 | 팔레트 표시명 | 설명 | 대표 사용 사례 | 지원 바인딩 | 이벤트 |
|------|-------------|------|---------------|------------|--------|
| `text` | Text | 정적/동적 텍스트 표시. variant(heading/label/body/caption)와 color(default/primary/muted/danger) 설정 가능 | KPI 라벨, 제목, 상태 값 표시 | state | -- |
| `markdown` | Markdown | 마크다운 형식 텍스트 렌더링. content 속성에 마크다운 문법 사용 | 설명문, 도움말, 서식 있는 텍스트 | state | -- |
| `button` | Button | 클릭 가능한 버튼. label, variant, disabled 속성 지원. 액션 체인 연결의 핵심 컴포넌트 | 조회, 저장, 삭제, 새로고침 | state | onClick |
| `input` | Input (form) | 텍스트 입력 필드. placeholder, inputType(text/number/email 등), name 속성 지원 | 검색어 입력, 필터 값 입력, 폼 필드 | state | onChange, onSubmit |
| `form` | Form | 여러 입력 컴포넌트를 묶는 컨테이너. title, submit_label 속성. 내부에 자식 컴포넌트 배치 가능 | 등록 폼, 수정 폼, 필터 영역 | state | onSubmit |
| `table` | DataTable | 데이터 테이블. columns/rows/selectable/sortable/page_size/row_click_action_index 속성. 조건부 스타일 지원 | 장비 목록, 이벤트 로그, 데이터 그리드 | state, result | onRowSelect, onRowClick |
| `chart` | Chart | 차트 시각화. chart_type(line/bar/pie/area/scatter), series, x_key, height 등 속성. 조건부 스타일 지원 | CPU 추이, 성능 모니터링, 통계 차트 | state, result | onHover, onClick |
| `badge` | Badge | 상태 표시 배지. label, variant(default/secondary/success/warning/danger/outline/ghost), color 속성. 조건부 스타일 지원 | 상태 인디케이터, 심각도 표시, 태그 | state | -- |
| `tabs` | Tabs | 탭 전환 컨테이너. tabs 배열과 activeIndex 속성 | 다중 뷰 전환, 카테고리 분리 | state | onTabChange |
| `accordion` | Accordion | 접이식 섹션 컨테이너. items 배열과 allow_multiple 속성 | FAQ, 상세 정보 접기/펴기 | state | onToggle |
| `modal` | Modal | 오버레이 대화상자. title, size(sm/md/lg), open 속성. 내부 자식 컴포넌트 배치 가능 | 상세보기, 등록/수정 폼, 확인 대화상자 | state | onOpen, onClose |
| `keyvalue` | KeyValue | 키-값 쌍 목록 표시. items 배열 속성 | 장비 상세 정보, 설정 값 표시 | state | -- |
| `divider` | Divider | 구분선. orientation(horizontal/vertical) 속성 | 섹션 구분, 레이아웃 분리 | -- | -- |
| `row` | Row (horizontal) | 수평 레이아웃 컨테이너. gap, align(start/center/end/stretch), justify(start/center/end/between/around) 속성. 자식 컴포넌트 배치 가능 | 버튼 그룹, KPI 카드 행, 수평 정렬 | -- | -- |
| `column` | Column (vertical) | 수직 레이아웃 컨테이너. gap, align(start/center/end/stretch) 속성. 자식 컴포넌트 배치 가능 | 폼 필드 그룹, 수직 정렬, 사이드바 | -- | -- |

참고: `row`, `column`, `modal`, `form`은 자식 컴포넌트를 내부에 배치할 수 있는 컨테이너 타입이다. 팔레트에서 이 컴포넌트를 선택한 상태로 다른 컴포넌트를 추가하면 자동으로 내부에 배치된다.

#### 0.2.2 레이아웃 타입 레퍼런스 (5종)

스키마의 `layout.type` 필드에 사용할 수 있는 레이아웃 타입이다.

| 레이아웃 타입 | 설명 | 대표 사용 사례 | 주요 속성 |
|-------------|------|---------------|----------|
| `grid` | 격자 기반 레이아웃. cols로 열 수 또는 열 크기 배열 지정, gap으로 간격 설정 | 대시보드 (KPI 카드 + 테이블 + 차트 복합) | cols, gap, spacing |
| `form` | 폼 중심 레이아웃. 입력 필드를 수직으로 나열하는 구조 | 등록/수정 폼, 설정 화면 | direction, spacing |
| `modal` | 모달 대화상자 기반 레이아웃. 오버레이로 표시 | 상세보기 팝업, 확인 대화상자 | max_width |
| `list` | 목록 기반 레이아웃. 반복 항목을 수직으로 나열 | 데이터 목록, 이벤트 리스트 | direction, spacing |
| `dashboard` | 대시보드 전용 레이아웃. 격자와 유사하되 반응형 최적화 | 운영 대시보드, 모니터링 화면 | cols, gap, max_width |

참고: 모든 레이아웃은 `direction`(horizontal/vertical) 속성으로 방향을 지정할 수 있으며, `spacing`(픽셀)으로 컴포넌트 간 간격을 설정한다.

#### 0.2.3 스키마 구조 다이어그램

Screen 하나의 전체 스키마 구조는 다음과 같다.

```text
ScreenSchemaV1
+-- screen_id (string, 필수)    --> 화면 고유 식별자
+-- name (string)               --> 표시 이름
+-- version (string)            --> 스키마 버전 (기본 "1.0")
+-- layout (object, 필수)       --> 레이아웃 정의
|   +-- type (LayoutType)       --> "grid" | "form" | "modal" | "list" | "dashboard"
|   +-- direction               --> "horizontal" | "vertical"
|   +-- spacing                 --> 픽셀 간격
|   +-- cols                    --> 열 수 또는 열 크기 배열
|   +-- gap                     --> 격자 간격
|   +-- max_width               --> CSS 최대 너비
|   +-- children                --> LayoutChild 배열 (중첩 레이아웃)
+-- components (array, 필수)    --> 컴포넌트 목록
|   +-- [n]
|       +-- id (string, 필수)   --> 컴포넌트 고유 ID
|       +-- type (string, 필수) --> 컴포넌트 타입
|       +-- label               --> 표시 라벨
|       +-- bind                --> 바인딩 경로 (state.xxx)
|       +-- props               --> 타입별 속성 객체
|       +-- visibility          --> { rule: "바인딩 표현식" }
|       +-- actions             --> ComponentActionRef 배열
+-- actions (array|null)        --> 화면 레벨 액션 목록
|   +-- [n]
|       +-- id (string, 필수)
|       +-- handler (string)    --> /ops/ui-actions 라우팅 키
|       +-- label
|       +-- endpoint
|       +-- payload_template
|       +-- context_required
+-- state (object|null, 필수)   --> 상태 정의
|   +-- initial                 --> 초기값 객체
|   +-- schema                  --> 각 키의 타입 정의
+-- bindings (object|null, 필수) --> 최상위 바인딩 맵
|   +-- "대상경로": "소스경로"
+-- metadata                    --> 메타 정보
|   +-- author, created_at, notes, tags
+-- theme                       --> 테마 설정
    +-- preset: "light"|"dark"|"brand"
    +-- overrides
```

#### 0.2.4 필수 필드와 선택 필드

| 필드 | 필수/선택 | 설명 |
|------|----------|------|
| `screen_id` | 필수 | 화면 고유 식별자. 변경 불가 |
| `layout` | 필수 | 레이아웃 정의 객체. 최소 `type` 필드 포함 |
| `components` | 필수 | 컴포넌트 배열. 빈 배열 가능 |
| `state` | 필수 | 상태 정의. `null` 가능하지만 동적 화면에서는 `initial` 필드 필요 |
| `bindings` | 필수 | 최상위 바인딩 맵. `null` 가능 |
| `actions` | 선택 | 화면 레벨 액션 배열. `null` 가능 |
| `name` | 선택 | 표시 이름 |
| `version` | 선택 | 기본값 "1.0" |
| `metadata` | 선택 | 작성자, 생성일, 메모, 태그 |
| `theme` | 선택 | 테마 프리셋 및 커스텀 오버라이드 |

컴포넌트 필수 필드:

| 필드 | 필수/선택 | 설명 |
|------|----------|------|
| `id` | 필수 | 컴포넌트 고유 ID. 같은 화면 내에서 중복 불가 |
| `type` | 필수 | 위 컴포넌트 타입 레퍼런스 참조 |
| `label` | 선택 | 편집기에서 표시되는 이름 |
| `bind` | 선택 | 상태 경로 바인딩 |
| `props` | 선택 | 타입별 속성 |
| `visibility` | 선택 | 조건부 표시 규칙 |
| `actions` | 선택 | 컴포넌트 레벨 액션 배열 |

#### 0.2.5 Screen 상태 흐름

Screen Asset은 두 가지 상태를 갖는다.

```text
[생성] --> draft --> [Publish] --> published --> [Rollback] --> draft
                 --> [Save Draft] --> draft (갱신)
                 --> [Delete] --> (삭제)
```

- **draft**: 편집 가능 상태. Visual/JSON/Binding/Action 탭에서 수정 가능. Save Draft로 저장
- **published**: 읽기 전용 상태. Visual 탭 진입 시 "Published screens are read-only" 메시지 표시. Rollback으로 draft로 전환 가능

---

## NEW: AI Copilot Assistant (⭐ 2026-02-14)

> **Availability**: Production Ready
> **Status**: ✅ Enabled by default
> **Learning Curve**: 5-10 minutes

### What is AI Copilot?

AI Copilot uses natural language to help you design screens faster. You describe what you want in plain English, and the system suggests JSON modifications to implement your idea.

**Example Commands**:
- "Add a button to submit the form"
- "Create a 3-column grid layout for the dashboard"
- "Change the title to red and make it bold"
- "Add a loading spinner when data is fetching"
- "Move the filter bar to the right side"

### How to Access Copilot

**Method 1**: From Visual Editor
1. Go to `/admin/screens/{screen_id}`
2. Click the **"✨ Copilot"** button in the toolbar (top-right)
3. Type your request in the text box
4. Review the suggestion and click **"Apply"** or **"Undo"**

**Method 2**: From Keyboard Shortcut
- Press `Ctrl+/` (Windows/Linux) or `Cmd+/` (Mac) to open Copilot
- Type your request
- Press Enter to generate suggestion

### Using Copilot Features

#### Natural Language Commands

Copilot understands context from your screen structure. Be specific:

**Good**:
- "Add a search input at the top of the table"
- "Create a modal dialog with a confirmation button"
- "Highlight error rows in red in the data table"

**Vague** (may not work as expected):
- "Make it look better"
- "Add a button"
- "Change colors"

#### Confidence Scores

Each Copilot suggestion shows a **confidence score** (0-100%):
- **90-100%**: Highly confident, safe to apply
- **70-89%**: Good suggestion, minor issues possible
- **50-69%**: Moderate confidence, review carefully
- **<50%**: Low confidence, may need manual adjustments

**Tip**: Always review suggestions before applying, especially for low-confidence scores.

#### Quick Action Buttons

After generating a suggestion, use these 6 buttons for quick modifications:

1. **Create** - Add a new component to the screen
2. **Move** - Reposition existing component
3. **Delete** - Remove component from screen
4. **Rename** - Change component label/ID
5. **Style** - Update component appearance (color, size, font)
6. **Layout** - Modify layout properties (grid, spacing, alignment)

**Example Workflow**:
1. Request: "Add a form section"
2. Copilot suggests a form layout
3. Confidence: 85%
4. Click **"Style"** to change form colors
5. Apply final version

### Best Practices

1. **Start Simple**: Begin with one component or layout change
2. **Describe Position**: "Top of page" or "Right sidebar" helps accuracy
3. **Reference Existing Components**: "Add a button next to the search input"
4. **Review Before Applying**: Check JSON changes match your intent
5. **Use Undo Liberally**: Click "Undo" to revert and try different wording

### Troubleshooting Copilot

| Issue | Solution |
|-------|----------|
| Suggestion doesn't match request | Try rephrasing with more specific terms |
| Component doesn't appear in preview | Check JSON tab to verify structure was added |
| Confidence score very low (< 50%) | Redo request with simpler, clearer language |
| Copilot button grayed out | Sign in to ensure LLM service is available |
| Undo not working | Refresh page and use browser back button |

### Limitations

- Copilot works best with English commands
- Complex multi-step designs may require manual JSON editing
- Copilot cannot directly call APIs or fetch data (use Binding tab for that)
- Some edge cases in conditional logic may need manual tuning

---

## NEW: Getting Started Tutorial (⭐ 2026-02-14)

> **Status**: ✅ Auto-launches on first login
> **Duration**: 5-7 minutes to complete
> **Availability**: Can be reset anytime

### What is the Onboarding Tutorial?

When you first access the Screen Editor, an interactive 7-step tutorial walks you through the core concepts and UI.

### Starting the Tutorial

**Auto-Start**: Opens automatically on your first visit to `/admin/screens`

**Manual Start**:
1. Click the **"?"** (Help) button in the top-right corner
2. Select **"Start Onboarding Tutorial"**
3. Follow the steps

### The 7 Steps

#### Step 1: Welcome
- Overview of Screen Editor capabilities
- Introduction to the main interface
- Quick tour of toolbar buttons

#### Step 2: Components
- Learn about component types (Button, Input, Table, etc.)
- How to drag components to canvas
- Basic component properties

#### Step 3: Properties Panel
- How to edit component properties
- Binding concepts (state, props)
- Common property configurations

#### Step 4: Canvas Editing
- Visual layout construction
- Grid/row/column concepts
- Responsive design basics

#### Step 5: Quick Action Buttons
- 6 quick action buttons for rapid editing
- Keyboard shortcuts for speed
- Saving draft changes

#### Step 6: Advanced Features
- AI Copilot assistant
- Binding tab for data connections
- Action tab for interactions

#### Step 7: Complete
- Summary of what you learned
- Next steps recommendation
- Link to detailed documentation

### Tracking Progress

The tutorial tracks your progress using localStorage:
- ✅ Completed steps are marked with checkmark
- ⏳ Current step is highlighted
- ⏭️ Skip to next step anytime

### Resetting Tutorial

To restart the tutorial:
1. Click "?" (Help) button
2. Select "Reset Onboarding Progress"
3. Tutorial will restart on next page load

### Completing the Tutorial

After finishing all 7 steps:
- You'll see a completion message
- Tutorial won't auto-appear on subsequent visits
- You can always restart using "Reset Onboarding Progress"

### Tips for Getting Most Out of Tutorial

1. **Take your time**: Each step has examples you can interact with
2. **Try it yourself**: Open VS code alongside and replicate examples
3. **Ask questions**: Use "Contact Support" link if anything is unclear
4. **Bookmark docs**: Save the link to this guide for reference

---

## 1. Lab 1 - 첫 Screen 생성

목표: 빈 화면에서 초안 Screen을 만든다.

### Step 1. 목록 화면 진입

1. `/admin/screens` 접속
2. 새 Screen 생성 버튼 클릭

### Step 2. 기본 정보 입력

- screen_id: `ops_device_overview`
- title: `Device Overview`
- description: 운영 장비 개요 화면

#### screen_id 네이밍 컨벤션

screen_id는 화면의 고유 식별자로서 생성 후 변경할 수 없다. 아래 규칙을 따른다.

| 규칙 | 올바른 예 | 잘못된 예 |
|------|----------|----------|
| snake_case 사용 | `ops_device_overview` | `OpsDeviceOverview` |
| 도메인 접두어 사용 | `ops_server_detail` | `server_detail` |
| 기능을 명확히 표현 | `maint_ticket_list` | `screen_001` |
| 영문 소문자+숫자+밑줄만 사용 | `mes_line_06_dashboard` | `mes-line-06` |

권장 접두어 목록:
- `ops_` : 운영 관련 화면
- `maint_` : 유지보수 관련 화면
- `admin_` : 관리자 전용 화면
- `dash_` : 대시보드 화면
- `detail_` : 상세보기 화면
- `form_` : 입력/등록 폼 화면

#### 템플릿 선택 가이드

"새 Screen 생성" 버튼을 클릭하면 Template Gallery가 표시된다. 두 가지 탭에서 템플릿을 선택할 수 있다.

**Built-in Templates 탭** (내장 템플릿):

| 템플릿 | 설명 | 적합한 화면 |
|--------|------|-----------|
| Read-only Detail | 장비/엔티티 상세 정보를 라벨-값 쌍으로 표시 | 장비 상세, 이벤트 상세, 설정 조회 |
| List + Filter | 검색/필터 기능이 포함된 데이터 그리드 | 장비 목록, 이벤트 로그, 검색 화면 |
| List + Modal CRUD | 데이터 그리드에 생성/수정 모달 포함 | 티켓 관리, 설정 항목 관리 |

**Published Screens 탭** (발행된 화면):
- 이미 발행된 화면을 복제하여 새 화면의 시작점으로 사용한다
- 태그 필터와 검색으로 원하는 화면을 찾을 수 있다
- 복제 시 screen_id와 name이 자동으로 새 값으로 대체된다

빈 화면부터 시작하려면 Template Gallery에서 아무것도 선택하지 않고 직접 생성한다.

#### 초기 스키마 전체 JSON 예시

템플릿 없이 빈 화면을 생성하면 아래와 유사한 초기 스키마가 만들어진다. 필수 필드가 모두 포함된 최소 구조이다.

```json
{
  "screen_id": "ops_device_overview",
  "name": "Device Overview",
  "version": "1.0",
  "layout": {
    "type": "dashboard",
    "direction": "vertical",
    "spacing": 16,
    "cols": 2,
    "gap": "16px"
  },
  "components": [],
  "actions": [],
  "state": {
    "initial": {},
    "schema": {}
  },
  "bindings": {},
  "metadata": {
    "author": null,
    "created_at": null,
    "notes": "운영 장비 개요 화면",
    "tags": {}
  },
  "theme": null
}
```

검증 포인트:
- Draft 상태로 목록에 생성된다.
- 목록에서 screen_id, name, status(draft) 칼럼이 정상 표시된다.
- 생성 직후 다시 목록을 새로고침해도 항목이 유지된다.

### Step 3. 편집기 진입

- 생성된 screen 클릭 -> `/admin/screens/{screen_id}`

검증 포인트:
- 편집기가 로딩되며 상단 헤더에 screen_id와 "draft" 상태가 표시된다.
- 좌측에 6개 탭(Visual, JSON, Binding, Action, Preview, Diff)이 표시된다.
- 우측에 AI Copilot 패널이 표시되며 레이아웃 타입과 컴포넌트 수가 요약된다.

---

## 2. Lab 2 - Visual 탭으로 레이아웃 만들기

목표: UI 뼈대를 완성한다.

Visual 탭의 화면 구성:
- 좌측(200px): Component Palette - 사용 가능한 컴포넌트 목록
- 중앙(가변): Canvas - 컴포넌트 배치 영역
- 우중앙(220px): Component Tree - 컴포넌트 계층 구조
- 우측(300px): Properties Panel - 선택된 컴포넌트 속성 편집

### Step 1. 컴포넌트 배치

장비 대시보드 예시를 단계별로 구성한다.

**1-1. 제목 영역 구성**

1. Component Palette에서 `Text` 클릭 (또는 드래그하여 Canvas에 놓기)
2. Properties Panel에서 속성 편집:
   - Label: `Dashboard Title`
   - content: `Device Dashboard`
   - variant: `heading` (드롭다운 선택)
   - color: `primary` (드롭다운 선택)

검증 포인트: Canvas에 "Device Dashboard" 텍스트가 heading 스타일로 표시된다.

**1-2. KPI 카드 행 구성**

1. Component Palette에서 `Row (horizontal)` 클릭하여 행 컨테이너 추가
2. Properties Panel에서 row 속성 편집:
   - Label: `KPI Row`
   - gap: `16`
   - justify: `between`
3. Component Tree에서 "KPI Row"가 선택된 상태를 확인
4. Palette 상단에 "Adding to: KPI Row" 표시 확인
5. `Badge` 클릭 3회 -> KPI Row 내부에 Badge 3개 추가
6. 각 Badge 선택 후 Properties Panel에서 편집:
   - Badge 1: label=`가용률`, variant=`success`
   - Badge 2: label=`평균 CPU`, variant=`default`
   - Badge 3: label=`알람 수`, variant=`danger`

검증 포인트: Component Tree에서 KPI Row 아래 3개 Badge가 자식으로 표시된다.

**1-3. 필터 입력 영역 구성**

1. Canvas 빈 영역 클릭하여 컨테이너 선택 해제 (또는 Escape 키)
2. `Row (horizontal)` 추가
   - Label: `Filter Row`
   - gap: `12`
3. Filter Row 선택 상태에서:
   - `Input (form)` 추가: placeholder=`장비 ID 입력`, name=`device_id`
   - `Input (form)` 추가: placeholder=`심각도 선택`, name=`severity`
   - `Button` 추가: label=`검색`, variant=`default`

**1-4. 데이터 테이블 구성**

1. Escape로 컨테이너 선택 해제
2. `DataTable` 클릭하여 테이블 추가
3. Properties Panel > Table Columns 아코디언 펼치기
4. "Add Column" 버튼으로 컬럼 4개 추가:
   - field: `timestamp`, header: `시간`, format: `datetime`, sortable: 체크
   - field: `device_id`, header: `장비 ID`, format: 없음, sortable: 체크
   - field: `event_type`, header: `이벤트 유형`, format: 없음, sortable: 체크
   - field: `severity`, header: `심각도`, format: 없음, sortable: 체크
5. Table Behavior 아코디언에서:
   - Sortable: 체크
   - Page Size: `20`

**1-5. 액션 버튼 영역 구성**

1. `Row (horizontal)` 추가: Label=`Action Buttons`, gap=`12`
2. 내부에 Button 2개 추가:
   - Button 1: label=`새로고침`
   - Button 2: label=`진단 실행`

### Step 2. 속성 편집

Properties Panel에서 편집 가능한 주요 속성을 컴포넌트 타입별로 정리한다.

**Text/Markdown 속성**:
- content: 표시할 텍스트. Static 모드에서 직접 입력하거나 Binding 모드에서 `{{state.xxx}}` 형태로 연결
- variant: heading / label / body / caption 중 선택
- color: default / primary / muted / danger 중 선택

**Button 속성**:
- label: 버튼에 표시할 텍스트
- variant: 버튼 스타일
- disabled: 비활성화 여부 (boolean 체크박스)

**Input 속성**:
- placeholder: 입력 전 안내 텍스트
- inputType: text / number / email 등
- name: 폼 데이터 키 이름

**Table 속성**:
- columns: Table Columns 아코디언에서 편집 (field, header, sortable, format)
- sortable: 전체 정렬 활성화
- page_size: 페이지당 행 수 (0이면 페이지네이션 비활성)
- row_click_action_index: 행 클릭 시 실행할 액션 인덱스 (-1이면 비활성)
- selectable: 행 선택 기능 활성화

**Chart 속성**:
- chart_type: line / bar / pie / area / scatter
- x_key: X축 데이터 키
- height: 차트 높이 (픽셀, 기본 400)
- series: Chart Behavior 아코디언에서 편집 (name, data_key, color)
- show_legend / show_grid / responsive: 체크박스
- y_min / y_max: Y축 범위
- y_axis / legend / tooltip: JSON 직접 편집

**Badge 속성**:
- label: 배지 텍스트
- variant: default / secondary / success / warning / danger / outline / ghost
- color: 색상 값

### Step 3. 편집 생산성 기능 사용

Visual 탭에서 사용 가능한 키보드 단축키 전체 목록:

| 단축키 | 동작 | 설명 |
|--------|------|------|
| `Ctrl+Z` | Undo | 마지막 변경 되돌리기 |
| `Ctrl+Shift+Z` | Redo | 되돌린 변경 다시 적용 |
| `Ctrl+A` | Select All | 모든 컴포넌트 선택 |
| `Ctrl+C` | Copy | 선택된 컴포넌트 복사 |
| `Ctrl+X` | Cut | 선택된 컴포넌트 잘라내기 |
| `Ctrl+V` | Paste | 복사된 컴포넌트 붙여넣기 |
| `Ctrl+D` | Duplicate | 선택된 컴포넌트 복제 |
| `Escape` | Deselect | 모든 선택 해제 |
| `Delete` | Delete | 선택된 컴포넌트 삭제 |
| `Ctrl+ArrowUp` | Move Up | 선택된 컴포넌트 위로 이동 |
| `Ctrl+ArrowDown` | Move Down | 선택된 컴포넌트 아래로 이동 |

참고: Mac에서는 `Ctrl` 대신 `Cmd` 키를 사용한다. 입력 필드(input, textarea)에 포커스가 있을 때는 단축키가 비활성화되어 정상적인 텍스트 편집이 가능하다.

**컴포넌트 드래그 앤 드롭**:
- Palette에서 컴포넌트를 Canvas로 직접 드래그하여 배치할 수 있다
- 드래그 중인 컴포넌트는 반투명 상태로 표시된다

**Properties Panel 하단 버튼**:
- Duplicate: 선택된 컴포넌트를 바로 아래에 복제
- Delete: 선택된 컴포넌트 삭제 (확인 대화상자 표시)

검증 포인트:
- 컴포넌트 트리가 의도대로 구성된다.
- Component Tree에서 부모-자식 관계가 올바르게 표시된다.
- 각 컴포넌트 선택 시 Properties Panel이 해당 타입의 속성을 표시한다.
- Undo/Redo로 변경 사항을 자유롭게 되돌릴 수 있다.

---

## 3. Lab 3 - JSON 탭으로 스키마 확인

목표: Visual 결과가 스키마에 어떻게 반영되는지 이해한다.

### Step 1. JSON 탭 이동

- 탭 바에서 "JSON" 클릭
- screen schema 전체 확인

JSON 편집기에는 현재 draft 스키마의 전체 JSON이 표시된다. Visual 탭에서 만든 구조가 JSON으로 어떻게 표현되는지 확인할 수 있다.

### Step 2. 핵심 필드 확인

Lab 2에서 구성한 장비 대시보드의 완성된 스키마 JSON 예시를 필드별로 확인한다.

```json
{
  "screen_id": "ops_device_overview",
  "name": "Device Overview",
  "version": "1.0",

  "layout": {
    "type": "dashboard",
    "direction": "vertical",
    "spacing": 16,
    "cols": 2,
    "gap": "16px"
  },

  "components": [
    {
      "id": "comp_title",
      "type": "text",
      "label": "Dashboard Title",
      "props": {
        "content": "Device Dashboard",
        "variant": "heading",
        "color": "primary"
      },
      "visibility": null,
      "actions": []
    },
    {
      "id": "comp_kpi_row",
      "type": "row",
      "label": "KPI Row",
      "props": {
        "gap": 16,
        "justify": "between",
        "components": [
          {
            "id": "comp_badge_avail",
            "type": "badge",
            "label": "가용률",
            "props": {
              "label": "{{state.kpi.availability}}%",
              "variant": "success"
            }
          },
          {
            "id": "comp_badge_cpu",
            "type": "badge",
            "label": "평균 CPU",
            "props": {
              "label": "{{state.kpi.avg_cpu}}%",
              "variant": "default"
            }
          },
          {
            "id": "comp_badge_alert",
            "type": "badge",
            "label": "알람 수",
            "props": {
              "label": "{{state.kpi.alert_count}}건",
              "variant": "danger"
            }
          }
        ]
      }
    },
    {
      "id": "comp_filter_row",
      "type": "row",
      "label": "Filter Row",
      "props": {
        "gap": 12,
        "components": [
          {
            "id": "comp_input_device",
            "type": "input",
            "label": "Device ID Input",
            "props": {
              "placeholder": "장비 ID 입력",
              "name": "device_id"
            }
          },
          {
            "id": "comp_input_severity",
            "type": "input",
            "label": "Severity Input",
            "props": {
              "placeholder": "심각도 선택",
              "name": "severity"
            }
          },
          {
            "id": "comp_btn_search",
            "type": "button",
            "label": "Search Button",
            "props": {
              "label": "검색"
            },
            "actions": [
              {
                "id": "action_search",
                "handler": "fetch_device_events",
                "payload_template": {
                  "device_id": "{{inputs.device_id}}",
                  "severity": "{{inputs.severity}}"
                }
              }
            ]
          }
        ]
      }
    },
    {
      "id": "comp_events_table",
      "type": "table",
      "label": "Events Table",
      "bind": "state.events",
      "props": {
        "columns": [
          { "field": "timestamp", "header": "시간", "sortable": true, "format": "datetime" },
          { "field": "device_id", "header": "장비 ID", "sortable": true, "format": "" },
          { "field": "event_type", "header": "이벤트 유형", "sortable": true, "format": "" },
          { "field": "severity", "header": "심각도", "sortable": true, "format": "" }
        ],
        "sortable": true,
        "page_size": 20,
        "selectable": false,
        "row_click_action_index": -1
      }
    },
    {
      "id": "comp_action_row",
      "type": "row",
      "label": "Action Buttons",
      "props": {
        "gap": 12,
        "components": [
          {
            "id": "comp_btn_refresh",
            "type": "button",
            "label": "Refresh",
            "props": { "label": "새로고침" },
            "actions": [
              {
                "id": "action_refresh",
                "handler": "fetch_device_events",
                "payload_template": {}
              }
            ]
          },
          {
            "id": "comp_btn_diagnose",
            "type": "button",
            "label": "Diagnose",
            "props": { "label": "진단 실행" },
            "actions": [
              {
                "id": "action_diagnose",
                "handler": "run_device_diagnosis",
                "payload_template": {
                  "device_id": "{{state.selected_device_id}}"
                }
              }
            ]
          }
        ]
      }
    }
  ],

  "actions": [
    {
      "id": "action_load_data",
      "label": "Load Dashboard Data",
      "handler": "fetch_device_overview",
      "payload_template": {},
      "context_required": ["tenant_id"]
    }
  ],

  "state": {
    "initial": {
      "kpi": {
        "availability": 0,
        "avg_cpu": 0,
        "alert_count": 0
      },
      "filters": {
        "device_id": "",
        "severity": "all"
      },
      "events": [],
      "selected_device_id": null,
      "last_message": ""
    },
    "schema": {
      "kpi": { "type": "object" },
      "filters": { "type": "object" },
      "events": { "type": "array" },
      "selected_device_id": { "type": "string" },
      "last_message": { "type": "string" }
    }
  },

  "bindings": {
    "events_table.rows": "state.events",
    "badge_avail.label": "state.kpi.availability",
    "badge_cpu.label": "state.kpi.avg_cpu",
    "badge_alert.label": "state.kpi.alert_count"
  },

  "metadata": {
    "author": "operator",
    "created_at": "2026-02-08T00:00:00Z",
    "notes": "운영 장비 개요 대시보드",
    "tags": {
      "domain": "ops",
      "priority": "high"
    }
  },

  "theme": null
}
```

**필드별 설명**:

| 필드 | 역할 |
|------|------|
| `layout.type` | 전체 레이아웃 모드. "dashboard"로 대시보드 최적화 |
| `layout.cols` | 기본 2열 격자 |
| `layout.gap` | 컴포넌트 간 간격 16px |
| `components[n].id` | 각 컴포넌트의 고유 식별자. 바인딩과 액션에서 참조 |
| `components[n].type` | 렌더러가 어떤 React 컴포넌트로 그릴지 결정 |
| `components[n].props` | 타입별 속성. text는 content/variant/color, table은 columns/rows 등 |
| `components[n].actions` | 컴포넌트에 연결된 액션 체인. onClick 등 이벤트에 반응 |
| `state.initial` | 화면 로드 시 초기 상태값. 모든 바인딩의 기본 데이터 |
| `state.schema` | 각 상태 키의 타입 정의. 편집기 유효성 검증에 사용 |
| `bindings` | 대상경로와 소스경로 매핑. 컴포넌트 속성을 상태 데이터에 연결 |
| `actions[n].handler` | `/ops/ui-actions` 엔드포인트로 라우팅되는 액션 ID |
| `actions[n].payload_template` | 액션 실행 시 전송할 데이터 템플릿 |

### Step 3. 간단 수정

JSON 탭에서 직접 스키마를 수정할 수 있다. 자주 사용하는 수정 패턴을 정리한다.

**패턴 1: 텍스트 내용 변경**
```json
// components[0].props.content 수정
"content": "Device Dashboard"  -->  "content": "장비 운영 대시보드"
```

**패턴 2: 컴포넌트 순서 변경**
```json
// components 배열에서 항목 순서를 바꾸면 렌더링 순서가 변경된다
"components": [comp_A, comp_B]  -->  "components": [comp_B, comp_A]
```

**패턴 3: 레이아웃 열 수 변경**
```json
// layout.cols 수정
"cols": 2  -->  "cols": 3
```

**패턴 4: 새 컴포넌트 추가**
```json
// components 배열에 새 항목 추가
{
  "id": "comp_new_divider",
  "type": "divider",
  "label": "Section Divider",
  "props": { "orientation": "horizontal" }
}
```

**패턴 5: 상태 초기값 변경**
```json
// state.initial에서 기본값 수정
"kpi": { "availability": 0, "avg_cpu": 0, "alert_count": 0 }
-->
"kpi": { "availability": 99.9, "avg_cpu": 45.2, "alert_count": 3 }
```

검증 포인트:
- JSON 수정 후 Visual에 반영된다.
- JSON 문법 오류 시 편집기가 오류를 표시한다.
- Visual 탭에서 변경한 내용이 JSON 탭으로 돌아오면 반영되어 있다.
- 유효하지 않은 컴포넌트 타입을 입력하면 validation error가 발생한다.

---

## 4. Lab 4 - Binding 탭으로 데이터 연결

목표: 컴포넌트가 정적 UI가 아니라 동적 UI로 동작하도록 만든다.

Binding 탭은 화면의 모든 바인딩을 한곳에서 관리하는 전용 편집 화면이다. 상단에 Binding Debugger Sample Data 영역이 있고, 아래에 바인딩 목록이 표시된다.

### Step 1. 기본 바인딩 추가

바인딩은 컴포넌트의 속성을 상태(state), 입력(inputs), 컨텍스트(context) 데이터에 연결하는 메커니즘이다.

#### 바인딩 표현식 문법 전체 레퍼런스

| 표현식 형식 | 설명 | 예시 |
|-------------|------|------|
| `{{state.키}}` | 화면 상태 데이터 참조 | `{{state.device_name}}` |
| `{{state.객체.키}}` | 중첩 상태 데이터 참조 | `{{state.kpi.availability}}` |
| `{{inputs.키}}` | 입력 파라미터 참조 | `{{inputs.device_id}}` |
| `{{context.키}}` | 컨텍스트 데이터 참조 (tenant_id 등) | `{{context.tenant_id}}` |
| `{{trace_id}}` | 현재 실행 추적 ID | `{{trace_id}}` |
| `state.키` | state 접두어만 사용 (중괄호 없이) | `state.events` |
| `context.키` | context 접두어만 사용 (중괄호 없이) | `context.userId` |
| `inputs.키` | inputs 접두어만 사용 (중괄호 없이) | `inputs.formData` |
| 정적 값 | 바인딩 없는 고정 값 | `hello`, `123` |

참고: `{{...}}` 형식과 접두어만 사용하는 형식 모두 지원된다. Properties Panel의 Binding 모드에서는 prefix 버튼(state, inputs, context, trace_id)을 클릭하여 빠르게 표현식을 삽입할 수 있다.

#### 바인딩 적용 예시

이 Lab에서 설정할 바인딩 목록:

| 대상 (Target Path) | 소스 (Source Path) | 설명 |
|-------------------|--------------------|------|
| `comp_badge_avail.label` | `{{state.kpi.availability}}` | 가용률 Badge에 KPI 데이터 연결 |
| `comp_badge_cpu.label` | `{{state.kpi.avg_cpu}}` | CPU Badge에 KPI 데이터 연결 |
| `comp_badge_alert.label` | `{{state.kpi.alert_count}}` | 알람 Badge에 KPI 데이터 연결 |
| `comp_events_table.rows` | `{{state.events}}` | 이벤트 테이블에 데이터 배열 연결 |
| `comp_title.content` | `Device Dashboard ({{inputs.device_name}})` | 제목에 장비명 반영 |
| `trace_text.content` | `{{trace_id}}` | 디버그용 추적 ID 표시 |

### Step 2. 경로 유효성 확인

바인딩 경로가 유효하지 않을 때의 동작을 확인한다.

**테스트 절차**:
1. 바인딩 목록에서 아무 항목 클릭
2. Source Path를 `state.nonexistent_field`로 변경
3. Binding Debugger에서 평가값 확인

**잘못된 경로의 동작**:
- 존재하지 않는 경로: 평가값이 `undefined`로 표시
- 중첩 경로 오류 (예: `state.kpi.nonexistent`): `undefined`
- 문법 오류 (예: `{{state.}`): Properties Panel의 PathPicker에서 빨간색 오류 메시지 표시

**경로 검증 함수**: `validateBindingPath()`가 스키마 기반으로 경로 유효성을 검증한다. 경고 메시지가 Properties Panel 하단에 표시된다.

### Step 3. Binding 평가 확인

Binding Debugger Sample Data 영역을 사용하여 바인딩 결과를 미리 확인한다.

**테스트 데이터 입력**:

state (JSON) 입력 영역에 아래 값을 입력한다.

```json
{
  "kpi": {
    "availability": 99.5,
    "avg_cpu": 42.3,
    "alert_count": 7
  },
  "events": [
    {"timestamp": "2026-02-08T10:00:00Z", "device_id": "DEV-001", "event_type": "cpu_high", "severity": "warning"},
    {"timestamp": "2026-02-08T09:30:00Z", "device_id": "DEV-002", "event_type": "disk_full", "severity": "critical"}
  ],
  "selected_device_id": "DEV-001"
}
```

context (JSON) 입력 영역에 아래 값을 입력한다.

```json
{
  "tenant_id": "t1",
  "user_id": "admin"
}
```

inputs (JSON) 입력 영역에 아래 값을 입력한다.

```json
{
  "device_name": "MES Server 06",
  "device_id": "DEV-006"
}
```

"Apply Sample Data" 버튼 클릭 후 바인딩 목록에서 각 항목의 평가값(value)을 확인한다.

검증 포인트:
- `{{state.kpi.availability}}` -> `99.5`
- `{{state.events}}` -> 2개 항목 배열
- `{{context.tenant_id}}` -> `"t1"`
- `{{inputs.device_name}}` -> `"MES Server 06"`
- `{{trace_id}}` -> `"(preview-trace-id)"`
- 유효 경로는 정상 평가
- 잘못된 경로는 즉시 식별 가능 (`undefined` 표시)
- JSON 파싱 오류 시 빨간색 에러 메시지 표시

---

## 5. Lab 5 - Action 탭으로 인터랙션 만들기

목표: 버튼 클릭으로 데이터 갱신/액션 실행.

Action 탭은 두 가지 범위의 액션을 관리한다:
- **Screen Actions**: 화면 전체에서 공유하는 재사용 가능한 액션
- **Component Actions**: 특정 컴포넌트에 연결된 액션 (Visual 탭에서 컴포넌트 선택 필요)

표시 모드도 두 가지가 있다:
- **List View**: 목록 형태로 액션 관리
- **Flow View**: ActionFlowVisualizer로 액션 체인을 시각적 플로우로 표시

### Step 1. 액션 추가

**Screen 레벨 액션 추가 (데이터 조회)**:

1. Action 탭에서 "Screen Actions" 버튼 선택 확인
2. "+ New Action" 버튼 클릭
3. 우측 편집 영역에서 설정:
   - Action ID: `action_load_data` (자동 생성된 값 확인)
   - Handler: `fetch_device_overview`
4. "Save" 버튼 클릭

**Handler 선택 시 Catalog 활용**:

Action Editor Modal에서 handler를 설정할 때, 시스템에 등록된 Action Catalog에서 선택할 수 있다. Catalog는 `/ops/ui-actions/catalog` API에서 로드된다.

Catalog에서 제공하는 정보:
- `action_id`: handler에 입력할 액션 식별자
- `label`: 액션의 표시 이름
- `description`: 액션 설명
- `input_schema`: 입력 파라미터 스키마 (payload_template 자동 생성에 활용)
- `output.state_patch_keys`: 액션이 반환하는 상태 키 목록
- `required_context`: 필수 컨텍스트 키 목록

Catalog가 로드되지 않을 경우 아래 기본 핸들러를 사용할 수 있다:
- `fetch_device_detail`
- `list_maintenance_filtered`
- `create_maintenance_ticket`
- `open_maintenance_modal`
- `close_maintenance_modal`

### Step 2. 입력 매핑 (payload_template)

액션의 payload_template은 실행 시 서버로 전송되는 데이터의 템플릿이다. 바인딩 표현식을 사용하여 동적 값을 매핑한다.

**완전한 액션 구성 JSON 예시 (Screen Action)**:

```json
{
  "id": "action_load_data",
  "label": "Load Dashboard Data",
  "handler": "fetch_device_overview",
  "endpoint": "/ops/ui-actions",
  "method": "POST",
  "payload_template": {
    "device_id": "{{inputs.device_id}}",
    "tenant_id": "{{context.tenant_id}}",
    "severity_filter": "{{state.filters.severity}}",
    "page": 1,
    "page_size": 20
  },
  "context_required": ["tenant_id"]
}
```

**완전한 액션 구성 JSON 예시 (Component Action)**:

```json
{
  "id": "action_search",
  "label": "Search Events",
  "handler": "fetch_device_events",
  "payload_template": {
    "device_id": "{{inputs.device_id}}",
    "severity": "{{inputs.severity}}"
  },
  "continue_on_error": false,
  "stop_on_error": true,
  "retry_count": 2,
  "retry_delay_ms": 1000,
  "run_if": "{{state.filters.device_id}}",
  "on_error_action_index": -1,
  "on_error_action_indexes": []
}
```

**payload_template 매핑 패턴**:

| 매핑 대상 | 표현식 | 설명 |
|----------|--------|------|
| 입력 파라미터 | `"{{inputs.device_id}}"` | 사용자 입력값 전달 |
| 현재 상태 | `"{{state.selected_device_id}}"` | 화면 상태 값 전달 |
| 컨텍스트 | `"{{context.tenant_id}}"` | 테넌트/사용자 정보 전달 |
| 중첩 상태 | `"{{state.filters.severity}}"` | 중첩 객체 경로 참조 |
| 정적 값 | `20` | 고정 숫자/문자열 직접 입력 |

### Step 3. 응답 매핑

액션 실행 결과는 화면 상태(state)에 자동으로 병합된다. 서버가 반환하는 `state_patch`가 현재 상태에 적용된다.

**서버 응답 예시**:

```json
{
  "trace_id": "tr-abc123",
  "state_patch": {
    "events": [
      {"timestamp": "2026-02-08T10:00:00Z", "device_id": "DEV-001", "event_type": "cpu_high", "severity": "warning"},
      {"timestamp": "2026-02-08T09:30:00Z", "device_id": "DEV-002", "event_type": "disk_full", "severity": "critical"}
    ],
    "kpi": {
      "availability": 99.5,
      "avg_cpu": 42.3,
      "alert_count": 7
    },
    "last_message": "조회 성공: 2건"
  }
}
```

**state 병합 결과**: `state_patch`의 각 키가 현재 state에 머지된다.
- `state.events` <- 서버가 반환한 events 배열
- `state.kpi` <- 서버가 반환한 kpi 객체
- `state.last_message` <- "조회 성공: 2건"

**에러 처리와 사용자 피드백**:

컴포넌트 액션의 실패 정책 프리셋 3가지:

| 프리셋 | continue_on_error | stop_on_error | retry_count | retry_delay_ms | 설명 |
|--------|-------------------|---------------|-------------|----------------|------|
| Strict Stop | false | true | 0 | 500 | 실패 즉시 체인 중단 |
| Best Effort | true | false | 0 | 500 | 실패해도 다음 액션 계속 |
| Retry Then Fallback | false | true | 2 | 1000 | 2회 재시도 후 중단 |

추가 에러 처리 필드:
- `run_if`: 조건 표현식. 조건이 falsy이면 액션을 건너뛴다. 예: `"{{state.selected_device_id}}"` (선택된 장비가 있을 때만 실행)
- `on_error_action_index`: 에러 발생 시 실행할 대체 액션의 인덱스
- `on_error_action_indexes`: 에러 발생 시 실행할 대체 액션 인덱스 배열

검증 포인트:
- 액션 실행 시 state patch 반영
- 오류 시 메시지가 표시
- Action 목록에서 handler가 "(unset)"이 아닌 실제 값으로 표시
- Flow View에서 액션 체인이 시각적으로 표시

---

## 6. Lab 6 - Preview 탭에서 실사용 검증

목표: 실제 사용 흐름을 미리 검증한다.

Preview 탭은 세 영역으로 구성된다:
1. **Preview Data Overrides**: 파라미터와 바인딩 오버라이드 입력
2. **Action Runner**: 액션을 수동/자동 실행하여 데이터 갱신 테스트
3. **렌더링 영역**: UIScreenRenderer로 화면을 실제 렌더링

### Step 1. Preview overrides 입력

**params JSON 입력**:

params 영역에 아래와 같이 입력한다. 이 값은 화면이 외부에서 호출될 때 전달받는 파라미터를 시뮬레이션한다.

```json
{
  "context": {
    "tenant_id": "t1",
    "user_id": "admin",
    "role": "operator"
  },
  "device_id": "DEV-006",
  "device_name": "MES Server 06"
}
```

**bindings override JSON 입력**:

bindings override 영역에 아래와 같이 입력한다. 기존 바인딩을 임시로 덮어쓸 수 있다.

```json
{
  "comp_events_table.rows": "state.test_events",
  "comp_badge_avail.label": "state.test_kpi.availability"
}
```

"Apply Preview Data" 버튼 클릭 후 렌더링 결과를 확인한다.

검증 포인트:
- params와 bindings override가 정상 적용된다.
- JSON 파싱 오류 시 빨간색 에러 메시지가 표시된다.
- "params must be a JSON object" 또는 "bindings must be a JSON object" 메시지로 유형 확인 가능

### Step 2. 렌더링 확인

**Viewport 전환**:

Viewport 드롭다운에서 세 가지 크기를 전환하며 반응형 동작을 확인한다.

| Viewport | 너비 | 사용 사례 |
|----------|------|----------|
| Desktop | 100% (전체 폭) | 일반 모니터에서의 표시 |
| Tablet | 820px | 태블릿 또는 좁은 모니터 |
| Mobile | 390px | 모바일 기기 |

**반응형 점검 항목**:
1. Desktop: 모든 컴포넌트가 의도대로 배치되는지 확인
2. Tablet: 2열 레이아웃이 적절히 축소되는지 확인
3. Mobile: 수평 Row 컴포넌트가 세로로 전환되는지, 테이블이 스크롤 가능한지 확인

**버튼 클릭 액션 실행 테스트**:

렌더링 영역에서 직접 버튼을 클릭하여 액션이 실행되는지 확인한다. 또는 Action Runner 영역을 사용한다.

### Step 3. Action Runner로 액션 실행 테스트

Action Runner 영역은 Preview 탭 상단에 위치하며, 등록된 Screen Action을 직접 실행할 수 있다.

**수동 실행**:
1. Action 드롭다운에서 실행할 액션 선택 (예: `action_load_data`)
2. Action payload 입력:

```json
{
  "device_id": "DEV-006",
  "tenant_id": "t1",
  "severity_filter": "all"
}
```

3. "Run Once" 버튼 클릭
4. "Latest action result" 영역에서 응답 확인

**자동 실행 (Auto-run)**:
1. Auto-run interval 입력: `15000` (15초 간격)
2. "Start Auto-run" 버튼 클릭
3. 설정된 간격으로 액션이 반복 실행됨
4. "Last auto-run:" 타임스탬프로 마지막 실행 시각 확인
5. 중지하려면 "Stop Auto-run" 클릭

Auto-run은 최소 1000ms(1초) 간격으로 설정 가능하다.

### Step 4. 결과 검증

**Latest action result 확인**:

성공 시:
```json
{
  "trace_id": "tr-abc123",
  "state_patch": {
    "events": [...],
    "kpi": {...}
  }
}
```

실패 시:
- 빨간색 에러 메시지가 "Action payload" 아래에 표시
- 예: "Failed to run action", "Invalid action payload JSON"

**Validation Errors 확인**:

스키마에 오류가 있으면 렌더링 영역 위에 "Preview has validation errors" 블록이 표시된다. 최대 3개의 오류가 경로(path)와 메시지(message)와 함께 표시된다.

검증 포인트:
- 주요 사용자 흐름이 끊기지 않는다.
- Desktop/Tablet/Mobile 모든 뷰포트에서 레이아웃이 정상 표시된다.
- 액션 실행 결과가 state에 반영되어 화면이 갱신된다.
- 에러 시 사용자에게 명확한 피드백이 제공된다.
- Auto-run이 설정된 간격으로 정상 실행된다.

---

## 7. Lab 7 - Diff 탭으로 변경점 점검

목표: draft와 published 차이를 정확히 검토한다.

### Step 1. Diff 탭 이동

- 컴포넌트/액션/바인딩/상태 차이 확인

### Step 2. 변경 요약 확인

- added/removed/modified 수치 확인

### Step 3. 의도하지 않은 변경 제거

- 불필요 수정 정리

검증 포인트:
- 발행 전에 변경 범위를 팀이 설명 가능

---

## 8. Lab 8 - Publish와 Rollback

목표: 배포 가능한 상태를 만든다.

### Step 1. Publish Gate 점검

- 스키마 유효성
- binding/action 유효성
- 권한/정책 점검

### Step 2. Publish

- Publish 실행
- 성공 메시지 확인

### Step 3. Runtime 검증

- 실제 호출 경로에서 렌더링 확인

### Step 4. Rollback

- 문제 발생 시 rollback 실행
- 이전 버전 정상동작 확인

검증 포인트:
- publish/rollback 모두 재현 가능

---

## 9. Lab 9 - 협업/Presence 확인

목표: 다중 편집 상황을 안전하게 운영한다.

### Step 1. Presence 표시 확인

- 탭 상단 active editors 확인

### Step 2. heartbeat/stream 동작 확인

- `/ops/ui-editor/presence/heartbeat`
- `/ops/ui-editor/presence/stream`
- `/ops/ui-editor/presence/leave`

검증 포인트:
- 동시 편집 세션이 표시된다.
- 연결 불안정 시 fallback이 동작한다.

---

## 10. 장애 대응 플레이북

### 10.1 화면이 비어 보임

점검 순서:
1. 필수 bindings 존재 여부
2. state 초기값
3. preview overrides 데이터

### 10.2 버튼이 동작하지 않음

점검 순서:
1. handler/action_id 설정
2. payload 매핑
3. 서버 응답/권한 오류

### 10.3 Publish 차단

점검 순서:
1. validation 메시지 확인
2. 잘못된 path/handler 수정
3. 다시 validate 후 publish

### 10.4 diff가 과도함

점검 순서:
1. 불필요 JSON 포맷 변경 제거
2. 의미 없는 속성 변경 되돌리기

---

## 11. 최종 체크리스트

```text
[ ] 빈 화면에서 Screen을 새로 만들었다.
[ ] Visual/JSON/Binding/Action/Preview/Diff를 모두 사용했다.
[ ] 액션 실행으로 state 갱신을 확인했다.
[ ] Publish와 Rollback을 각각 수행했다.
[ ] Presence 기반 동시 편집 상황을 확인했다.
```

---

## 12. 참고 파일

- `apps/web/src/app/admin/screens/page.tsx`
- `apps/web/src/app/admin/screens/[screenId]/page.tsx`
- `apps/web/src/components/admin/screen-editor/ScreenEditor.tsx`
- `apps/web/src/components/admin/screen-editor/ScreenEditorTabs.tsx`
- `apps/web/src/components/admin/screen-editor/preview/PreviewTab.tsx`
- `apps/web/src/components/admin/screen-editor/diff/DiffTab.tsx`
- `apps/web/src/components/answer/UIScreenRenderer.tsx`
- `apps/api/app/modules/ops/router.py`
- `apps/web/src/lib/ui-screen/screen.schema.ts`
- `apps/web/src/lib/ui-screen/component-registry.ts`
- `apps/web/src/lib/ui-screen/screen-templates.ts`
- `apps/web/src/components/admin/screen-editor/visual/ComponentPalette.tsx`
- `apps/web/src/components/admin/screen-editor/visual/PropertiesPanel.tsx`
- `apps/web/src/components/admin/screen-editor/binding/BindingTab.tsx`
- `apps/web/src/components/admin/screen-editor/actions/ActionTab.tsx`
- `apps/web/src/components/admin/screen-editor/actions/ActionEditorModal.tsx`
- `apps/web/src/components/admin/screen-editor/templates/TemplateGallery.tsx`


---

## 13. Lab 10 - Table 고급 동작 구성

목표: 테이블을 운영 친화적으로 구성.

### Step 1. 컬럼 정의

- field/header 매핑
- sortable 설정
- 포맷터(number/date/percent)

### Step 2. 페이지네이션

- page_size 설정

### Step 3. 행 클릭 액션

- `row_click_action_index` 지정

검증 포인트:
- 정렬/페이지/행 액션이 모두 동작한다.

---

## 14. Lab 11 - Auto Refresh 구성

목표: 화면이 주기적으로 데이터를 갱신하도록 설정.

### Step 1. auto_refresh 활성화

예시:
```json
{
  "enabled": true,
  "interval_ms": 30000,
  "action_index": 0,
  "max_failures": 3,
  "backoff_ms": 10000
}
```

### Step 2. Preview에서 동작 확인

- 주기 실행 여부
- 실패 시 백오프/중단 확인

검증 포인트:
- 불필요한 과호출 없이 안정적으로 갱신된다.

---

## 15. Lab 12 - Action 체인 구성

목표: 여러 액션을 순서대로 실행하는 화면 구성.

### Step 1. 액션 3개 구성

1. 데이터 조회
2. 상태 병합
3. 사용자 메시지 표시

### Step 2. 실패 정책 설정

- stop_on_error
- continue_on_error
- retry_count/retry_delay

### Step 3. Preview에서 체인 테스트

검증 포인트:
- 성공/실패 경로가 예측 가능하게 동작한다.

---

## 16. Lab 13 - Direct API Endpoint 액션 실습

목표: `/ops/ui-actions` 외 endpoint 직접 호출 흐름 익히기.

### Step 1. 액션 모드 설정

- endpoint: 예 `/admin/system/health`
- method: `GET`

### Step 2. response_mapping 설정

예시:
```json
{
  "cpu_usage": "health.resource.cpu_percent",
  "memory_usage": "health.resource.memory_percent"
}
```

### Step 3. Preview 실행

검증 포인트:
- 응답이 state 키로 매핑된다.
- 경로 오타 시 즉시 에러 확인 가능

---

## 17. Lab 14 - Inspector 연계 디버깅

목표: 화면 액션 실패를 trace로 추적.

### Step 1. 실패 액션 실행

- Preview에서 의도적 잘못된 payload 사용

### Step 2. Inspector 이동

- trace_id 기준 `/admin/inspector` 열기

### Step 3. 확인 항목

- action 요청 payload
- tool_calls/references
- 오류 메시지

검증 포인트:
- UI 오류를 API/액션 레벨 원인으로 설명 가능

---

## 18. Lab 15 - 릴리즈 전 최종 리허설

목표: 발행 직전 최종 점검 루틴 확립.

### 체크 순서

1. Visual에서 레이아웃 깨짐 확인
2. Binding 경로 누락 확인
3. Action 정상/오류 경로 확인
4. Preview 모바일 확인
5. Diff 의도치 않은 변경 제거
6. Publish Gate 통과

### 발행 후 즉시 확인

1. Runtime 렌더링
2. 핵심 액션 1회 실행
3. 로그/오류율 확인

---

## 19. 운영 부록 - 디자인/운영 표준

### 화면 설계 표준

- 핵심 KPI는 상단
- 필터는 좌상단
- 상세 테이블은 중앙
- 에러 메시지는 사용자 행동 근처

### 바인딩 표준

- 긴 경로는 중간 state로 분리
- 공통 경로 네이밍 일관성 유지

### 액션 표준

- handler 이름은 동사형
- payload 키는 snake_case로 통일
- 실패 메시지는 사용자 관점 문구 사용

---

## 20. 운영 부록 - 빠른 복구 체크

문제 발생 시 5분 복구 루틴:

1. Preview에서 재현
2. Action payload 확인
3. Inspector trace 확인
4. 임시 조치(버튼 비활성/조건 완화)
5. rollback 또는 hotfix publish


---

## 21. 완성 프로젝트 트랙 - 운영 대시보드 화면 1개 완성

목표: 실제 운영자가 사용하는 화면을 빈 상태에서 완성한다.

완성 목표 화면:
1. 상단 KPI 카드 3개
2. 필터 영역 1개
3. 메인 테이블 1개
4. 상세 패널 1개
5. 새로고침/진단 버튼 2개

### 21.1 설계 초안 작성

먼저 스케치를 글로 정의한다.

```text
- Header: Device Dashboard
- Row 1: KPI(availability, avg_cpu, alert_count)
- Row 2 Left: Filter (device_id, severity)
- Row 2 Right: Table (latest events)
- Footer: Action buttons (refresh, diagnose)
```

### 21.2 Visual 구현

순서:
1. Container 배치
2. KPI Text/Badge 배치
3. Filter input/select 배치
4. Table 배치
5. Button 배치

검증 포인트:
- 레이아웃만으로도 읽기 가능한 UI가 된다.

### 21.3 상태 모델 정의

`state` 최소 필드:

```json
{
  "kpi": {"availability": 0, "avg_cpu": 0, "alert_count": 0},
  "filters": {"device_id": "", "severity": "all"},
  "events": [],
  "selected_event": null,
  "last_message": ""
}
```

검증 포인트:
- 모든 컴포넌트가 참조할 기본 state가 있다.

### 21.4 바인딩 연결

예시:
- KPI 텍스트 <- `{{state.kpi.availability}}`
- Table rows <- `{{state.events}}`
- 상세패널 <- `{{state.selected_event}}`

검증 포인트:
- 미연결 컴포넌트가 남지 않는다.

### 21.5 액션 체인 연결

버튼 `refresh` 체인:
1. 데이터 조회 액션
2. state merge
3. 성공 메시지 표시

버튼 `diagnose` 체인:
1. 선택 이벤트 검증
2. 진단 API 호출
3. 결과 상태 반영

검증 포인트:
- 두 버튼 모두 성공/실패 경로가 분리된다.

### 21.6 Preview 종합 점검

필수 점검:
1. Desktop/Tablet/Mobile
2. 필터 입력 동작
3. 테이블 정렬/페이지
4. 버튼 액션
5. 실패 메시지

### 21.7 Publish & Runtime 검증

1. Diff 확인
2. Publish Gate 통과
3. Runtime 호출에서 동일 동작 확인

### 21.8 Rollback 리허설

1. 의도적 오류 변경
2. publish 시도/실패 또는 런타임 오류 확인
3. rollback 수행
4. 정상 복귀 확인

완료 판정:

```text
[ ] 운영 대시보드 1개를 빈 상태에서 완성
[ ] 액션 체인 2개가 정상 동작
[ ] publish/rollback 모두 검증
[ ] 모바일 포함 사용성 확인 완료
```

---

## 22. 인수인계 패키지 작성법

화면 배포 후 아래 문서를 반드시 남긴다.

1. 화면 목적
2. 주요 컴포넌트 설명
3. 필수 bindings 목록
4. 액션 handler 목록
5. 실패 시 복구 절차

샘플 템플릿:

```text
[Screen 운영 인수인계]
screen_id:
owner:

핵심 액션:
- refresh_data
- run_diagnosis

주의사항:
- selected_event 없으면 diagnose 실행 금지
- API timeout 시 재시도 1회

복구:
- rollback to previous published
```

---

## 23. 팀 운영 규칙 샘플

1. Publish 전 Diff 검토 필수
2. Binding 경로 검증 실패 상태에서 배포 금지
3. 액션 실패 메시지 없는 화면 배포 금지
4. 신규 화면은 모바일 체크 필수
5. 주요 화면은 rollback 리허설 후 배포
