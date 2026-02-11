import type { CenterTab, CepDraft, DraftStatus } from "./types";
import {
  extractJsonCandidates,
  stripCodeFences,
  tryParseJson,
} from "../copilot/json-utils";

export const normalizeBaseUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "";

export const parseJsonObject = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }
  return JSON.parse(trimmed);
};

export const validateCepDraftShape = (draft: CepDraft) => {
  if (!draft.rule_name?.trim()) {
    return "draft.rule_name 값이 필요합니다.";
  }
  if (!draft.trigger || typeof draft.trigger !== "object") {
    return "draft.trigger는 JSON 객체여야 합니다.";
  }
  if (draft.actions && !Array.isArray(draft.actions)) {
    return "draft.actions는 배열이어야 합니다.";
  }
  if (draft.conditions && !Array.isArray(draft.conditions)) {
    return "draft.conditions는 배열이어야 합니다.";
  }
  return null;
};

export const parseCepDraft = (text: string) => {
  const rawCandidates = [stripCodeFences(text), text];
  let lastError: string | null = null;

  const tryNormalize = (payload: unknown) => {
    if (typeof payload !== "object" || payload === null) return null;
    const obj = payload as Record<string, unknown>;

    if (obj.type !== "cep_draft") {
      // tolerate direct draft object shape for lenient parsing
      if (obj.rule_name && obj.trigger) {
        const directDraft = obj as unknown as CepDraft;
        const directShapeError = validateCepDraftShape(directDraft);
        if (!directShapeError) return { ok: true as const, draft: directDraft, notes: null as string | null };
      }
      lastError = "type=cep_draft인 객체가 아닙니다.";
      return null;
    }

    if (!obj.draft || typeof obj.draft !== "object") {
      lastError = "draft 필드가 없습니다.";
      return null;
    }
    const draft = obj.draft as CepDraft;
    const shapeError = validateCepDraftShape(draft);
    if (shapeError) {
      lastError = shapeError;
      return null;
    }
    return { ok: true as const, draft, notes: (obj.notes as string) ?? null };
  };

  for (const candidate of rawCandidates) {
    if (!candidate.trim()) continue;

    const direct = tryParseJson(candidate);
    const directResult = tryNormalize(direct);
    if (directResult) return directResult;

    const extractedCandidates = extractJsonCandidates(candidate);
    for (const extracted of extractedCandidates) {
      const parsed = tryParseJson(extracted);
      const normalized = tryNormalize(parsed);
      if (normalized) return normalized;
    }
  }

  return { ok: false as const, error: lastError ?? "JSON 객체를 추출할 수 없습니다." };
};

export const tabOptions: { id: CenterTab; label: string }[] = [
  { id: "definition", label: "JSON Editor" },
  { id: "definition-form", label: "Form Builder" },
  { id: "test", label: "Test" },
  { id: "logs", label: "Logs" },
];

export const DRAFT_STORAGE_PREFIX = "cep-builder:draft:";
export const FINAL_STORAGE_PREFIX = "cep-builder:rule:";

export const draftStatusLabels: Record<DraftStatus, string> = {
  idle: "대기 중",
  draft_ready: "드래프트 준비됨",
  previewing: "미리보기",
  testing: "테스트 중",
  applied: "폼 적용됨",
  saved: "저장됨",
  outdated: "드래프트 오래됨",
  error: "오류 발생",
};

export const COPILOT_INSTRUCTION = `
You are a CEP Rule Generator for Tobit's monitoring system.
Generate intelligent CEP rules based on user descriptions.

ALWAYS return exactly one JSON object with type=cep_draft. NO markdown, NO code blocks.

Important guidelines:
1. Support complex conditions using AND/OR/NOT logic
2. Include composite_condition when multiple conditions are specified
3. Provide trigger_spec with value_path for metric triggers
4. Suggest appropriate aggregation (avg, sum, max, etc.)
5. Add meaningful actions (webhook, notify, etc.)

Example for user input: "Alert when CPU exceeds 80% OR memory exceeds 70%"

{
  "type":"cep_draft",
  "draft":{
    "rule_name":"High CPU or Memory Usage Alert",
    "description":"Alert when CPU usage exceeds 80% or memory usage exceeds 70%",
    "trigger_type":"metric",
    "trigger_spec":{
      "endpoint":"/api/metrics/system",
      "value_path":"data.metrics",
      "method":"GET"
    },
    "composite_condition":{
      "logic":"OR",
      "conditions":[
        {"field":"cpu_percent","op":">","value":80},
        {"field":"memory_percent","op":">","value":70}
      ]
    },
    "actions":[
      {
        "type":"webhook",
        "endpoint":"https://api.example.com/alerts",
        "method":"POST"
      }
    ]
  }
}

Only output raw JSON without additional explanation or markdown.
`;

export const CEP_COPILOT_EXAMPLE_PROMPTS: string[] = [
  "CPU 사용률이 85%를 5분 이상 넘으면 Slack 경고",
  "에러 로그가 1분에 100건 이상이면 PagerDuty 트리거",
  "주문 실패율이 3% 초과 시 webhook 호출",
  "DB 커넥션 수가 90% 이상이면 자동 스케일아웃 API 호출",
  "메모리 누수 징후(10분 연속 증가) 감지 시 알림",
  "서비스 다운 이벤트 발생 시 SMS + Email 동시 발송",
  "응답시간 p95가 800ms 초과하면 티켓 생성",
  "새 릴리즈 후 에러율 급증 시 롤백 워크플로우 실행",
  "결제 실패 이벤트가 특정 국가에서 급증하면 차단 액션",
  "디스크 사용량 95% 이상이면 로그 정리 스크립트 실행",
  "API 429 비율 증가 시 rate-limit 정책 강화 호출",
  "테넌트별 SLA 위반 징후를 감지하고 보고서 생성",
];

/**
 * CEP 드래프트 Diff 계산
 * 원본과 드래프트의 차이점을 계산하여 변경 사항 목록 반환
 */
export const computeCepDraftDiff = (draft: CepDraft, baseline: CepDraft | null | undefined): string[] => {
  const changes: string[] = [];

  if (!baseline) {
    return ["새로운 규칙 생성"];
  }

  // rule_name 변경
  if (draft.rule_name !== baseline.rule_name) {
    changes.push(`규칙명: "${baseline.rule_name}" → "${draft.rule_name}"`);
  }

  // description 변경
  const descDiff = (draft.description ?? "") !== (baseline.description ?? "");
  if (descDiff) {
    if (!baseline.description) {
      changes.push(`설명 추가: "${draft.description}"`);
    } else if (!draft.description) {
      changes.push(`설명 제거`);
    } else {
      changes.push(`설명 변경`);
    }
  }

  // trigger_spec 변경
  const triggerDiff = JSON.stringify(draft.trigger) !== JSON.stringify(baseline.trigger);
  if (triggerDiff) {
    changes.push(`트리거 스펙 변경`);
  }

  // composite_condition 변경
  const conditionDiff = JSON.stringify(draft.conditions) !== JSON.stringify(baseline.conditions);
  if (conditionDiff) {
    const conditionCount = (draft.conditions ?? []).length;
    changes.push(`조건 변경 (${conditionCount}개 조건)`);
  }

  // actions 변경
  const actionDiff = JSON.stringify(draft.actions) !== JSON.stringify(baseline.actions);
  if (actionDiff) {
    const actionCount = (draft.actions ?? []).length;
    changes.push(`액션 변경 (${actionCount}개 액션)`);
  }

  // enrichments 변경
  const enrichmentDiff = JSON.stringify(draft.enrichments) !== JSON.stringify(baseline.enrichments);
  if (enrichmentDiff) {
    const enrichmentCount = (draft.enrichments ?? []).length;
    changes.push(`보강 변경 (${enrichmentCount}개 보강)`);
  }

  return changes.length > 0 ? changes : ["변경 사항이 없습니다."];
};
