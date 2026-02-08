/**
 * API Manager utility functions
 * Extracted from api-manager/page.tsx for reusability
 */

import type {
  ApiDefinitionItem,
  ApiDraft,
  HttpLogic,
  LogicType,
  ScopeType,
} from "./types";

// ─── Constants ───

export const DEFAULT_SCOPE: ScopeType = "custom";
export const DEFAULT_TAB = "definition" as const;
export const SCOPE_LABELS: Record<ScopeType, string> = {
  custom: "custom",
  system: "system",
};

export const logicTypeLabels: Record<LogicType, string> = {
  sql: "SQL",
  workflow: "Workflow",
  python: "Python script",
  script: "Script",
  http: "HTTP",
};

export const DRAFT_STORAGE_PREFIX = "api-manager:draft:";
export const FINAL_STORAGE_PREFIX = "api-manager:api:";

export const tabOptions: { id: "definition" | "logic" | "test"; label: string }[] = [
  { id: "definition", label: "Definition" },
  { id: "logic", label: "Logic" },
  { id: "test", label: "Test" },
];

export const draftStatusLabels: Record<string, string> = {
  idle: "대기 중",
  draft_ready: "드래프트 준비됨",
  previewing: "미리보기",
  testing: "테스트 중",
  applied: "폼 적용됨",
  saved: "로컬 저장됨",
  outdated: "드래프트 오래됨",
  error: "오류 발생",
};

// ─── Helpers ───

export const normalizeBaseUrl = (value: string | undefined) => {
  const url = value?.replace(/\/+$/, "");
  return url && url.length > 0 ? url : "";
};

export const buildApiUrl = (endpoint: string, baseUrl: string) => {
  if (baseUrl) {
    return `${baseUrl}${endpoint}`;
  }
  return endpoint;
};

export const formatTimestamp = (value: string) => {
  if (!value) return "";
  try {
    let dateStr = value;
    if (value.includes("T") && !value.endsWith("Z") && !/[+-]\d{2}:?\d{2}$/.test(value)) {
      dateStr = `${value}Z`;
    }
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString("ko-KR", {
      timeZone: "Asia/Seoul",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
};

export const buildStatusMessage = (selected: ApiDefinitionItem | null) => {
  if (!selected) {
    return "Select an API to view or edit its definition.";
  }
  return `Last updated ${formatTimestamp(selected.updated_at)} by ${selected.created_by ?? "unknown"}`;
};

export const parseTags = (value: string) =>
  value
    .split(",")
    .map((token) => token.trim())
    .filter(Boolean);

export const getEditorLanguage = (logicType: LogicType, scriptLanguage: "python" | "javascript") => {
  if (logicType === "sql") return "sql";
  if (logicType === "workflow" || logicType === "http") return "json";
  if (logicType === "python") return "python";
  return scriptLanguage;
};

export const formatJson = (value: Record<string, unknown> | null | undefined) =>
  JSON.stringify(value ?? {}, null, 2);

export const parseJsonObject = (value: string, label: string) => {
  const trimmed = value.trim();
  if (!trimmed) return {};
  const parsed = JSON.parse(trimmed);
  if (Array.isArray(parsed) || typeof parsed !== "object" || parsed === null) {
    throw new Error(`${label} must be a JSON object`);
  }
  return parsed;
};

export const safeParseJson = (value: string, fallback: Record<string, unknown> = {}) => {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
};

// ─── Draft operations ───

export const applyPatchToDraft = (base: ApiDraft, patchOps: { op: string; path: string; value: unknown }[]): ApiDraft => {
  const draftClone = JSON.parse(JSON.stringify(base)) as Record<string, unknown>;
  for (const op of patchOps ?? []) {
    if (op.op !== "replace") continue;
    const segments = op.path.split("/").filter(Boolean);
    if (segments.length === 0) continue;
    let cursor: Record<string, unknown> | unknown[] = draftClone;
    for (let idx = 0; idx < segments.length - 1; idx += 1) {
      const segment = segments[idx];
      const numericIndex = Number.parseInt(segment, 10);
      if (!Number.isNaN(numericIndex) && Number.isInteger(numericIndex)) {
        if (!Array.isArray(cursor)) cursor = [];
        if (!cursor[numericIndex]) cursor[numericIndex] = {};
        cursor = cursor[numericIndex] as Record<string, unknown> | unknown[];
        continue;
      }
      if (typeof (cursor as Record<string, unknown>)[segment] === "undefined" || (cursor as Record<string, unknown>)[segment] === null) {
        (cursor as Record<string, unknown>)[segment] = {};
      }
      cursor = (cursor as Record<string, unknown>)[segment] as Record<string, unknown> | unknown[];
    }
    const lastSegment = segments[segments.length - 1];
    const numericLast = Number.parseInt(lastSegment, 10);
    if (!Number.isNaN(numericLast) && Number.isInteger(numericLast)) {
      if (!Array.isArray(cursor)) cursor = [];
      cursor[numericLast] = op.value;
    } else {
      (cursor as Record<string, unknown>)[lastSegment] = op.value;
    }
  }
  return draftClone as ApiDraft;
};

export const validateDraftShape = (draft: ApiDraft) => {
  if (!draft.api_name?.trim()) return "draft.api_name 값이 필요합니다.";
  if (!draft.method) return "draft.method 값이 필요합니다.";
  if (!draft.endpoint?.trim()) return "draft.endpoint 값이 필요합니다.";
  if (!draft.logic) return "draft.logic 값이 필요합니다.";
  if (draft.logic.type === "sql") {
    if (!draft.logic.query?.trim()) return "draft.logic.query 값이 필요합니다.";
  } else if (draft.logic.type === "http") {
    if (!draft.logic.spec?.url) return "draft.logic.spec.url 값이 필요합니다.";
    if (!draft.logic.spec?.method) return "draft.logic.spec.method 값이 필요합니다.";
  } else {
    return `지원하지 않는 logic.type 입니다: ${(draft.logic as { type?: string }).type}`;
  }
  return null;
};

export const normalizeApiDraft = (input: Record<string, unknown>): ApiDraft => {
  const draft: ApiDraft = {
    api_name: String(input.api_name || "").trim(),
    method: (String(input.method || "GET").toUpperCase()) as "GET" | "POST" | "PUT" | "DELETE",
    endpoint: String(input.endpoint || "").trim(),
    description: String(input.description || "").trim(),
    tags: Array.isArray(input.tags) ? input.tags : [],
    params_schema: (input.params_schema as Record<string, unknown>) || {},
    runtime_policy: (input.runtime_policy as Record<string, unknown>) || {},
    is_active: typeof input.is_active === "boolean" ? input.is_active : true,
    logic: { type: "sql", query: "" },
  };

  const logicInput = input.logic as Record<string, unknown> | undefined;
  if (logicInput?.type === "http") {
    const httpSpec = (logicInput.spec || logicInput.request) as Record<string, unknown> | undefined;
    draft.logic = {
      type: "http",
      spec: {
        method: String(httpSpec?.method || "GET"),
        url: String(httpSpec?.url || ""),
        headers: (httpSpec?.headers as Record<string, string>) || {},
        params: (httpSpec?.params as Record<string, unknown>) || {},
        body: httpSpec?.body,
      },
    };
  } else {
    draft.logic = { type: "sql", query: String(logicInput?.query || "") };
  }
  return draft;
};

export const stripCodeFences = (value: string) => {
  const match = value.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (match && match[1]) return match[1].trim();
  return value.trim();
};

export const tryParseJson = (text: string) => {
  try { return JSON.parse(text); } catch { return null; }
};

export const extractJsonObjectFrom = (text: string, startIdx: number) => {
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = startIdx; i < text.length; i += 1) {
    const char = text[i];
    if (escape) { escape = false; continue; }
    if (char === "\\") { escape = true; continue; }
    if (char === '"') { inString = !inString; continue; }
    if (inString) continue;
    if (char === "{") depth += 1;
    if (char === "}") {
      depth -= 1;
      if (depth === 0) return text.slice(startIdx, i + 1);
    }
  }
  if (depth > 0 && !inString) return text.slice(startIdx) + "}".repeat(depth);
  throw new Error("JSON 객체를 추출하지 못했습니다.");
};

export const extractJsonCandidates = (text: string) => {
  const candidates: string[] = [];
  let searchIdx = text.indexOf("{");
  while (searchIdx !== -1 && searchIdx < text.length) {
    try {
      const candidate = extractJsonObjectFrom(text, searchIdx);
      if (candidate.trim()) candidates.push(candidate);
      searchIdx = text.indexOf("{", searchIdx + candidate.length);
    } catch {
      searchIdx = text.indexOf("{", searchIdx + 1);
    }
  }
  return candidates;
};

export const normalizeDraftPayload = (payload: unknown, baseDraft: ApiDraft) => {
  if (typeof payload !== "object" || payload === null) {
    return { ok: false as const, error: "JSON이 객체가 아닙니다." };
  }
  const obj = payload as Record<string, unknown>;
  if (obj.type !== "api_draft") {
    if (obj.api_name && (obj.endpoint || obj.logic)) {
      const draft = normalizeApiDraft(obj);
      const shapeError = validateDraftShape(draft);
      if (!shapeError) return { ok: true as const, draft, notes: (obj.notes as string) ?? null };
    }
    return { ok: false as const, error: "type=api_draft인 객체가 아닙니다." };
  }
  const mode = obj.mode;
  if (mode === "replace" || typeof mode === "undefined") {
    if (!obj.draft || typeof obj.draft !== "object") {
      return { ok: false as const, error: "draft 필드가 없습니다." };
    }
    const rawDraft = obj.draft as Record<string, unknown>;
    if (rawDraft?.logic && typeof rawDraft.logic === "object" && rawDraft.logic !== null) {
      const logic = rawDraft.logic as Record<string, unknown>;
      if (logic.type === "http" && logic.request && !logic.spec) {
        logic.spec = logic.request;
      }
    }
    const draft = normalizeApiDraft(rawDraft);
    const shapeError = validateDraftShape(draft);
    if (shapeError) return { ok: false as const, error: shapeError };
    return { ok: true as const, draft, notes: (obj.notes as string) ?? null };
  }
  if (mode === "patch") {
    if (!Array.isArray(obj.patch)) {
      return { ok: false as const, error: "patch 배열이 필요합니다." };
    }
    const patched = applyPatchToDraft(baseDraft, obj.patch as { op: string; path: string; value: unknown }[]);
    if (patched?.logic?.type === "http" && "request" in patched.logic && !("spec" in patched.logic)) {
      const logicWithRequest = patched.logic as HttpLogic & Record<string, unknown>;
      const legacyRequest = logicWithRequest.request;
      if (legacyRequest) {
        (patched as ApiDraft).logic = {
          ...logicWithRequest,
          spec: legacyRequest as Record<string, unknown>,
        } as HttpLogic;
      }
    }
    const draft = normalizeApiDraft(patched);
    const shapeError = validateDraftShape(draft);
    if (shapeError) return { ok: false as const, error: shapeError };
    return { ok: true as const, draft, notes: (obj.notes as string) ?? null };
  }
  return { ok: false as const, error: "mode는 replace 또는 patch여야 합니다." };
};

export const parseApiDraft = (text: string, baseDraft: ApiDraft) => {
  const rawCandidates = [stripCodeFences(text), text];
  let lastError: string | null = null;
  const tryNormalize = (payload: Record<string, unknown>) => {
    if (payload.type !== "api_draft") return null;
    const normalized = normalizeDraftPayload(payload, baseDraft);
    if (normalized.ok) return normalized;
    if (normalized.error) lastError = normalized.error;
    return null;
  };

  for (const candidate of rawCandidates) {
    if (!candidate.trim()) continue;
    const direct = tryParseJson(candidate);
    if (direct && typeof direct === "object" && direct !== null) {
      const normalized = tryNormalize(direct as Record<string, unknown>);
      if (normalized) return normalized;
    }
    const extractedCandidates = extractJsonCandidates(candidate);
    for (const extracted of extractedCandidates) {
      try {
        const parsed = JSON.parse(extracted);
        if (typeof parsed !== "object" || parsed === null) continue;
        const normalized = tryNormalize(parsed as Record<string, unknown>);
        if (normalized) return normalized;
      } catch { /* ignore */ }
    }
  }
  return { ok: false as const, error: lastError ?? "JSON 객체를 추출할 수 없습니다." };
};

export const apiToDraft = (api: ApiDefinitionItem): ApiDraft => {
  const draft: ApiDraft = {
    api_name: api.api_name,
    method: api.method,
    endpoint: api.endpoint,
    description: api.description ?? "",
    tags: api.tags ?? [],
    params_schema: api.param_schema ?? {},
    runtime_policy: api.runtime_policy ?? {},
    is_active: api.is_active ?? true,
    logic: { type: "sql", query: "" },
  };
  if (api.logic_type === "http") {
    draft.logic = { type: "http", spec: safeParseJson(api.logic_body, { method: "GET", url: "" }) };
  } else {
    draft.logic = { type: "sql", query: api.logic_body };
  }
  return draft;
};

export const buildTemporaryApiFromDraft = (draft: ApiDraft): ApiDefinitionItem => ({
  api_id: "applied-draft-temp",
  api_name: `[NEW] ${draft.api_name || "Unsaved Draft"}`,
  api_type: "custom",
  method: draft.method || "GET",
  endpoint: draft.endpoint || "",
  logic_type: draft.logic.type || "sql",
  logic_body: draft.logic.type === "sql" ? draft.logic.query : JSON.stringify(draft.logic.spec || {}),
  description: draft.description || "",
  tags: draft.tags || [],
  is_active: typeof draft.is_active === "boolean" ? draft.is_active : true,
  created_by: "AI Assistant",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  param_schema: draft.params_schema || {},
  runtime_policy: draft.runtime_policy || {},
  logic_spec: draft.logic.type === "http" ? draft.logic.spec || {} : {},
  source: "local",
});

export const validateSql = (query: string) => {
  const errors: string[] = [];
  const warnings: string[] = [];
  const normalized = query.trim();
  if (!normalized) {
    errors.push("SQL 쿼리가 비어 있습니다.");
    return { ok: false, errors, warnings };
  }
  const sanitized = normalized.replace(/;+\s*$/, "");
  const statements = sanitized.split(";").map((s) => s.trim()).filter(Boolean);
  if (statements.length > 1) errors.push("단일 SELECT 문만 허용합니다.");
  const upperQuery = statements[0]?.toUpperCase() ?? "";
  if (!upperQuery.startsWith("SELECT")) errors.push("SELECT 문만 허용됩니다.");
  const bannedKeywords = ["DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE", "INSERT", "UPDATE", "DELETE"];
  for (const keyword of bannedKeywords) {
    if (new RegExp(`\\b${keyword}\\b`, "i").test(normalized)) {
      errors.push(`${keyword} 키워드가 포함되어 있어 실행할 수 없습니다.`);
    }
  }
  if (normalized.includes(";") && statements.length === 1) {
    warnings.push("쿼리 끝에 세미콜론은 선택 사항입니다.");
  }
  return { ok: errors.length === 0, errors, warnings };
};

export const validateApiDraft = (draft: ApiDraft) => {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (!draft.api_name.trim()) errors.push("API 이름을 입력해야 합니다.");
  if (!draft.endpoint.startsWith("/")) errors.push("엔드포인트는 /로 시작해야 합니다.");
  if (!["GET", "POST", "PUT", "DELETE"].includes(draft.method)) {
    errors.push("HTTP 메서드는 GET/POST/PUT/DELETE 중 하나여야 합니다.");
  }
  if (draft.logic.type === "sql") {
    if (!draft.logic.query.trim()) errors.push("SQL 쿼리를 입력해야 합니다.");
    const sqlResult = validateSql(draft.logic.query);
    errors.push(...sqlResult.errors);
    warnings.push(...sqlResult.warnings);
  } else if (draft.logic.type === "http") {
    if (!draft.logic.spec.url) errors.push("HTTP Logic에 URL은 필수입니다.");
  } else {
    errors.push(`지원하지 않는 로직 타입입니다: ${(draft.logic as { type?: string }).type}`);
  }
  return { ok: errors.length === 0, errors, warnings };
};

export const computeDraftDiff = (draft: ApiDraft, baseline: ApiDraft) => {
  const differences: string[] = [];
  if (draft.api_name !== baseline.api_name) differences.push(`Name: ${baseline.api_name || "<empty>"} → ${draft.api_name || "<empty>"}`);
  if (draft.method !== baseline.method) differences.push(`Method: ${baseline.method} → ${draft.method}`);
  if (draft.endpoint !== baseline.endpoint) differences.push(`Endpoint: ${baseline.endpoint || "<empty>"} → ${draft.endpoint || "<empty>"}`);
  if (draft.description !== baseline.description) differences.push("Description changed");
  if ((draft.tags || []).join(",") !== (baseline.tags || []).join(",")) {
    differences.push(`Tags: ${(baseline.tags || []).join(", ") || "<empty>"} → ${(draft.tags || []).join(", ") || "<empty>"}`);
  }
  if (draft.logic.type !== baseline.logic.type) differences.push(`Logic type: ${baseline.logic.type} → ${draft.logic.type}`);
  if (draft.logic.type === "sql" && baseline.logic.type === "sql") {
    if (draft.logic.query !== baseline.logic.query) differences.push("Logic query updated");
  } else if (draft.logic.type === "http" && baseline.logic.type === "http") {
    if (JSON.stringify(draft.logic.spec) !== JSON.stringify(baseline.logic.spec)) differences.push("Logic HTTP spec updated");
  } else {
    differences.push("Logic body updated");
  }
  return differences;
};
