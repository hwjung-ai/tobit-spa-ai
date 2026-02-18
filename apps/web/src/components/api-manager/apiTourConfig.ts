import type { TourConfig } from "@/lib/onboarding/types";

/**
 * API Manager Onboarding Tour Configuration
 *
 * This tour guides users through the API Manager interface,
 * explaining how to create, configure, and test dynamic APIs.
 *
 * Target elements use data-testid attributes for reliable selection.
 * Make sure the corresponding elements have these testid attributes.
 */
export const API_TOUR_CONFIG: TourConfig = {
  id: "api-manager",
  name: "API Manager Tour",
  storageKey: "api-manager-tour-completed",
  steps: [
    {
      id: "welcome",
      title: "API Manager에 오신 것을 환영합니다!",
      content:
        "이곳에서 동적 API를 생성하고 관리할 수 있습니다. SQL 쿼리, HTTP 요청, Python 스크립트, 워크플로우 등 다양한 방식으로 API 로직을 정의할 수 있습니다. 7단계 투어를 시작합니다.",
      target: "[data-testid='api-manager-container']",
      placement: "bottom",
      skipable: true,
    },
    {
      id: "scope-selector",
      title: "스코프 선택",
      content:
        "Custom (사용자 정의 API) 또는 System (시스템 API) 스코프를 선택할 수 있습니다. System API는 읽기 전용이며, 필요시 Custom으로 가져와 편집할 수 있습니다.",
      target: "[data-testid='api-scope-selector']",
      placement: "bottom",
      skipable: true,
    },
    {
      id: "api-list",
      title: "API 목록",
      content:
        "좌측 패널에서 기존 API를 선택하거나 'New' 버튼으로 새 API를 만들 수 있습니다. 검색창과 필터를 사용해 API를 빠르게 찾을 수 있습니다.",
      target: "[data-testid='api-list']",
      placement: "right",
      skipable: true,
    },
    {
      id: "definition-tab",
      title: "Definition 탭",
      content:
        "API의 기본 정보를 정의합니다: API 이름, HTTP 메서드 (GET/POST/PUT/DELETE), 엔드포인트 경로, 설명, 태그 등을 설정할 수 있습니다.",
      target: "[data-testid='tab-definition']",
      placement: "bottom",
      skipable: true,
    },
    {
      id: "logic-tab",
      title: "Logic 탭",
      content:
        "API의 실제 로직을 작성합니다. SQL (데이터베이스 쿼리), HTTP (외부 API 호출), Python (스크립트 실행), Workflow (다단계 프로세스)를 지원합니다.",
      target: "[data-testid='tab-logic']",
      placement: "bottom",
      skipable: true,
    },
    {
      id: "test-tab",
      title: "Test 탭",
      content:
        "API를 직접 테스트하고 응답을 확인할 수 있습니다. 파라미터를 입력하고 Execute 버튼을 클릭하면 실제 결과를 볼 수 있습니다.",
      target: "[data-testid='tab-test']",
      placement: "bottom",
      skipable: true,
    },
    {
      id: "logs-tab",
      title: "Logs 탭",
      content:
        "API 실행 로그를 확인할 수 있습니다. 성공/실패 여부, 실행 시간, 에러 메시지 등의 정보를 제공합니다.",
      target: "[data-testid='tab-logs']",
      placement: "bottom",
      skipable: true,
    },
    {
      id: "copilot",
      title: "AI Copilot",
      content:
        "자연어로 API를 생성할 수 있습니다. 예: '사용자 목록을 조회하는 GET API 만들어줘' 와 같이 입력하면 AI가 API 정의와 로직을 자동으로 생성합니다.",
      target: "[data-testid='api-copilot-panel']",
      placement: "left",
      skipable: true,
    },
  ],
};

/**
 * Quick tour for returning users who want a refresher
 * A shorter version focusing on key features only
 */
export const API_QUICK_TOUR_CONFIG: TourConfig = {
  id: "api-manager-quick",
  name: "API Manager Quick Tour",
  storageKey: "api-manager-quick-tour-completed",
  steps: [
    {
      id: "quick-start",
      title: "빠른 시작",
      content:
        "AI Copilot에게 자연어로 API를 설명하면 자동으로 생성됩니다. 또는 Definition 탭에서 직접 API 정보를 입력하고 Logic 탭에서 로직을 작성할 수 있습니다.",
      target: "[data-testid='api-copilot-panel']",
      placement: "left",
      skipable: true,
    },
    {
      id: "quick-test",
      title: "테스트 및 배포",
      content:
        "Test 탭에서 API를 테스트한 후, Save 버튼으로 저장하세요. 서버가 연결되지 않은 경우 로컬 저장소에 임시 저장됩니다.",
      target: "[data-testid='tab-test']",
      placement: "bottom",
      skipable: true,
    },
  ],
};

export default API_TOUR_CONFIG;
