import type { TourConfig } from "@/lib/onboarding/types";

/**
 * CEP Builder Onboarding Tour Configuration
 *
 * This tour guides users through the CEP (Complex Event Processing) Rule Builder
 * interface, explaining the key components and workflow.
 *
 * Target elements use data-testid attributes for reliable selection.
 * Make sure the corresponding elements have these testid attributes.
 */
export const CEP_TOUR_CONFIG: TourConfig = {
  id: "cep-builder",
  name: "CEP Builder Tour",
  storageKey: "cep-builder-tour-completed",
  steps: [
    {
      id: "welcome",
      title: "CEP Rule Builder에 오신 것을 환영합니다!",
      content:
        "이곳에서 이벤트 처리 규칙을 만들 수 있습니다. CEP(Complex Event Processing)를 통해 실시간으로 이벤트를 분석하고 자동으로 대응할 수 있습니다. 6단계 투어를 시작합니다.",
      target: "[data-testid='cep-builder-container']",
      placement: "bottom",
      skipable: true,
    },
    {
      id: "rule-list",
      title: "규칙 목록",
      content:
        "좌측 패널에서 기존 규칙을 선택하거나 'New' 버튼으로 새 규칙을 만들 수 있습니다. 검색창을 사용해 규칙을 빠르게 찾을 수 있습니다.",
      target: "[data-testid='cep-rule-list']",
      placement: "right",
      skipable: true,
    },
    {
      id: "tabs",
      title: "편집 탭",
      content:
        "Definition (JSON 편집), Form Builder (폼 기반 편집), Test (시뮬레이션), Logs (실행 로그) 탭을 전환하여 규칙을 관리할 수 있습니다.",
      target: "[data-testid='cep-tabs']",
      placement: "bottom",
      skipable: true,
    },
    {
      id: "trigger-section",
      title: "트리거 설정",
      content:
        "규칙이 언제 실행될지 정의합니다. Metric (메트릭 기반), Event (이벤트 기반), Schedule (스케줄), Anomaly (이상 탐지) 중 선택할 수 있습니다.",
      target: "[data-testid='cep-trigger-section']",
      placement: "right",
      skipable: true,
    },
    {
      id: "conditions-section",
      title: "조건 설정",
      content:
        "AND/OR/NOT 논리 연산자를 사용하여 복합 조건을 구성할 수 있습니다. 각 조건은 필드, 연산자, 값으로 구성됩니다.",
      target: "[data-testid='cep-conditions-section']",
      placement: "right",
      skipable: true,
    },
    {
      id: "actions-section",
      title: "액션 설정",
      content:
        "조건 충족 시 실행할 액션을 정의합니다. Webhook, Slack, Email, SMS 등 다양한 알림 채널을 지원합니다.",
      target: "[data-testid='cep-actions-section']",
      placement: "right",
      skipable: true,
    },
    {
      id: "copilot",
      title: "AI Copilot",
      content:
        "자연어로 규칙을 생성할 수 있습니다. 예: 'CPU 사용률이 80%를 넘으면 Slack으로 알림 보내줘' 와 같이 입력하면 AI가 규칙을 자동으로 생성합니다.",
      target: "[data-testid='cep-copilot-panel']",
      placement: "left",
      skipable: true,
    },
  ],
};

/**
 * Quick tour for returning users who want a refresher
 * A shorter version focusing on key features only
 */
export const CEP_QUICK_TOUR_CONFIG: TourConfig = {
  id: "cep-builder-quick",
  name: "CEP Builder Quick Tour",
  storageKey: "cep-builder-quick-tour-completed",
  steps: [
    {
      id: "quick-start",
      title: "빠른 시작",
      content:
        "AI Copilot에게 자연어로 규칙을 설명하면 자동으로 생성됩니다. 또는 Form Builder 탭에서 직접 규칙을 구성할 수 있습니다.",
      target: "[data-testid='cep-copilot-panel']",
      placement: "left",
      skipable: true,
    },
    {
      id: "quick-test",
      title: "테스트 및 배포",
      content:
        "Test 탭에서 규칙을 시뮬레이션한 후, Save 버튼으로 저장하세요. 로컬 저장과 서버 저장이 모두 지원됩니다.",
      target: "[data-testid='cep-test-section']",
      placement: "right",
      skipable: true,
    },
  ],
};

export default CEP_TOUR_CONFIG;
