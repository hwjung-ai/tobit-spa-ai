# Screen Editor User Guide (업데이트됨)

**Last Updated**: 2026-02-10

## 1. 개요
Screen Editor는 코딩 없이 UI 화면을 구성하고 백엔드 로직(Action)을 연결할 수 있는 도구입니다. 이 가이드는 **화면 생성부터 액션 연결까지의 전체 흐름**을 단계별로 설명합니다.

---

## 2. 화면 구성하기 (Visual Tab)

가장 먼저 Visual 탭에서 화면의 뼈대를 만듭니다.

### 2.1 컴포넌트 추가
1. 좌측 **Component Palette**에서 원하는 컴포넌트(예: `Button`, `Chart`, `Table`)를 클릭하거나 중앙 Canvas로 드래그합니다.
2. 컴포넌트가 계층 구조(Tree)에 추가됩니다. `Row`나 `Column` 같은 컨테이너를 먼저 배치하고 그 안에 자식 컴포넌트를 넣는 것이 좋습니다.

### 2.2 속성 설정 (Properties)
컴포넌트를 선택하면 우측 **Properties Panel**에서 속성을 수정할 수 있습니다.
*   **Label/Content**: 화면에 표시될 텍스트
*   **Color/Variant**: 색상 및 스타일 (Primary, Danger 등)
*   **Props**: 각 컴포넌트 고유의 설정 (Chart의 경우 데이터 키, Table의 경우 컬럼 정의 등)

---

## 3. 데이터 연결하기 (Binding Tab)

화면을 동적으로 만들기 위해 컴포넌트 속성에 데이터를 연결합니다.

### 3.1 바인딩 문법
*   `{{state.key}}`: 서버에서 받은 상태 데이터
*   `{{inputs.key}}`: 사용자가 입력한 데이터
*   `{{context.key}}`: 사용자 정보 등 컨텍스트 데이터

### 3.2 바인딩 적용 방법
1. **Properties Panel**의 입력 필드 옆에 있는 **(B)** 아이콘이나 **Bind 모드**를 활성화합니다.
2. 바인딩 표현식을 입력합니다. (예: `{{state.cpu_usage}}%`)
3. **Binding 탭**에서 전체 바인딩 목록을 관리하고, 샘플 데이터를 넣어 정상적으로 값이 표시되는지 미리 확인할 수 있습니다.

---

## 4. 액션 및 핸들러 연결 (Action Tab & Catalog)

버튼 클릭이나 화면 로딩 시 데이터를 가져오거나 로직을 실행하도록 설정합니다.

### 4.1 액션의 종류
*   **Built-in Handlers**: 시스템에 내장된 기본 핸들러 (예: `fetch_system_health`)
*   **API Manager API**: 사용자가 API Manager에서 직접 만든 API

### 4.2 액션 생성 및 핸들러 선택 **(중요)**
1. **Action 탭**으로 이동하여 **Screen Actions** (화면 전역) 또는 **Component Actions** (특정 버튼 등)를 선택합니다.
2. **+ New Action**을 클릭합니다.
3. 우측 편집 패널의 **Handler** 드롭다운 메뉴를 클릭합니다.
4. **Catalog** 목록에서 원하는 핸들러를 선택합니다.
    *   목록에는 내장 핸들러와 API Manager에서 생성한 API가 모두 표시됩니다.
    *   선택 시 **설명, 필요 입력값(Input), 반환 데이터(Output Key)**가 즉시 표시되므로 소스 코드를 확인할 필요가 없습니다.

### 4.3 Payload 설정
선택한 핸들러가 요구하는 입력값을 `Payload Template`에 매핑합니다.
*   예: `{"device_id": "{{inputs.device_id}}"}`

---

## 5. 테스트 및 검증 (Preview Tab)

구성한 화면과 액션이 정상 동작하는지 즉시 확인합니다.

### 5.1 화면 렌더링 확인 (Preview Data)
*   **Params/Bindings Override** 영역에 테스트용 JSON 데이터를 입력하면 실제 화면처럼 렌더링됩니다.
*   반응형 뷰포트(Desktop/Tablet/Mobile)를 전환하며 레이아웃이 깨지지 않는지 점검합니다.

### 5.2 액션 실행 테스트 (Action Runner)
1. **Action Runner** 영역에서 테스트할 액션(예: `fetch_cep_stats`)을 선택합니다.
2. **Run Once** 버튼을 클릭합니다.
3. **Latest action result** 창에 서버로부터 돌아온 실제 데이터(JSON)가 표시됩니다.
4. **Auto-run** 기능을 켜면 설정한 간격(예: 5초)마다 자동으로 호출되어 실시간 데이터 변화를 확인할 수 있습니다.

---

## 6. 배포 (Publish)

작업이 완료되면 **Publish** 버튼을 눌러 실제 사용자에게 화면을 공개합니다. 언제든 **Rollback**을 통해 이전 버전으로 되돌릴 수 있습니다.
