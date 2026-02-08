import type { CenterTab, CepDraft, DraftStatus } from "./types";

export const normalizeBaseUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "";

export const parseJsonObject = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }
  return JSON.parse(trimmed);
};

export const stripCodeFences = (value: string) => {
  const match = value.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (match && match[1]) {
    return match[1].trim();
  }
  return value.trim();
};

export const extractFirstJsonObject = (text: string) => {
  const startIdx = text.indexOf("{");
  if (startIdx === -1) {
    throw new Error("JSON 객체가 포함되어 있지 않습니다.");
  }
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = startIdx; i < text.length; i += 1) {
    const char = text[i];
    if (escape) {
      escape = false;
      continue;
    }
    if (char === "\\") {
      escape = true;
      continue;
    }
    if (char === '"') {
      inString = !inString;
      continue;
    }
    if (inString) {
      continue;
    }
    if (char === "{") {
      depth += 1;
    }
    if (char === "}") {
      depth -= 1;
      if (depth === 0) {
        return text.slice(startIdx, i + 1);
      }
    }
  }
  if (depth > 0 && !inString) {
    return text.slice(startIdx) + "}".repeat(depth);
  }
  throw new Error("JSON 객체를 추출하지 못했습니다.");
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
  const candidates = [stripCodeFences(text), text];
  for (const candidate of candidates) {
    if (!candidate.trim()) {
      continue;
    }
    let parsed: unknown = null;
    try {
      parsed = JSON.parse(candidate);
    } catch {
      const extracted = extractFirstJsonObject(candidate);
      parsed = JSON.parse(extracted);
    }
    if (typeof parsed !== "object" || parsed === null) {
      continue;
    }
    const obj = parsed as Record<string, unknown>;
    if (obj.type !== "cep_draft") {
      return { ok: false, error: "type=cep_draft인 객체가 아닙니다." };
    }
    if (!obj.draft || typeof obj.draft !== "object") {
      return { ok: false, error: "draft 필드가 없습니다." };
    }
    const draft = obj.draft as CepDraft;
    const shapeError = validateCepDraftShape(draft);
    if (shapeError) {
      return { ok: false, error: shapeError };
    }
    return { ok: true, draft, notes: (obj.notes as string) ?? null };
  }
  return { ok: false, error: "JSON 객체를 추출할 수 없습니다." };
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
