"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import BuilderShell from "../../components/builder/BuilderShell";
import BuilderCopilotPanel from "../../components/chat/BuilderCopilotPanel";
import { saveApiWithFallback } from "../../lib/apiManagerSave";
import Editor from "@monaco-editor/react";

type ScopeType = "system" | "custom";
type CenterTab = "definition" | "logic" | "test";
type LogicType = "sql" | "workflow" | "python" | "script" | "http";
type SystemView = "discovered" | "registered";

interface ApiDefinitionItem {
  api_id: string;
  api_name: string;
  api_type: ScopeType;
  method: "GET" | "POST" | "PUT" | "DELETE";
  endpoint: string;
  logic_type: LogicType;
  logic_body: string;
  description: string | null;
  tags: string[];
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  param_schema: Record<string, unknown>;
  runtime_policy: Record<string, unknown>;
  logic_spec: Record<string, unknown>;
  source?: ApiSource;
}

type ApiSource = "server" | "local";

interface SystemApiItem extends ApiDefinitionItem {
  source: ApiSource;
}

interface DiscoveredEndpoint {
  method: string;
  path: string;
  operationId?: string | null;
  summary?: string | null;
  description?: string | null;
  tags?: string[];
  parameters?: unknown[];
  requestBody?: Record<string, unknown> | null;
  responses?: Record<string, unknown> | null;
  source: "openapi" | "router";
}

interface ExecuteResult {
  executed_sql: string;
  params: Record<string, unknown>;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  duration_ms: number;
}

interface ExecLogEntry {
  exec_id: string;
  executed_at: string;
  executed_by: string | null;
  status: string;
  duration_ms: number;
  row_count: number;
  request_params: Record<string, unknown> | null;
  error_message: string | null;
}

interface WorkflowStepResult {
  node_id: string;
  node_type: "sql" | "script";
  status: "success" | "fail";
  duration_ms: number;
  row_count: number;
  columns?: string[];
  output?: Record<string, unknown>;
  error_message?: string | null;
  references?: Record<string, unknown>;
}

interface WorkflowExecuteResult {
  steps: WorkflowStepResult[];
  final_output: Record<string, unknown>;
  references: Record<string, unknown>[];
}

const buildTemporaryApiFromDraft = (draft: ApiDraft): ApiDefinitionItem => ({
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

const DEFAULT_SCOPE: ScopeType = "custom";
const DEFAULT_TAB: CenterTab = "definition";
const SCOPE_LABELS: Record<ScopeType, string> = {
  custom: "custom",
  system: "system",
};

const normalizeBaseUrl = (value: string | undefined) => {
  const url = value?.replace(/\/+$/, "");
  // Return empty string to use Next.js rewrites proxy instead of direct API calls
  return url && url.length > 0 ? url : "";
};

// Helper to build API URL - uses relative path when baseUrl is empty
const buildApiUrl = (endpoint: string, baseUrl: string) => {
  if (baseUrl) {
    return `${baseUrl}${endpoint}`;
  }
  return endpoint; // Use relative path for Next.js rewrites
};

const formatTimestamp = (value: string) => {
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

const buildStatusMessage = (selected: ApiDefinitionItem | null) => {
  if (!selected) {
    return "Select an API to view or edit its definition.";
  }
  return `Last updated ${formatTimestamp(selected.updated_at)} by ${selected.created_by ?? "unknown"}`;
};

const parseTags = (value: string) =>
  value
    .split(",")
    .map((token) => token.trim())
    .filter(Boolean);

const logicTypeLabels: Record<LogicType, string> = {
  sql: "SQL",
  workflow: "Workflow",
  python: "Python script",
  script: "Script",
  http: "HTTP",
};

const getEditorLanguage = (logicType: LogicType, scriptLanguage: "python" | "javascript") => {
  if (logicType === "sql") {
    return "sql";
  }
  if (logicType === "workflow" || logicType === "http") {
    return "json";
  }
  if (logicType === "python") {
    return "python";
  }
  return scriptLanguage;
};

const formatJson = (value: Record<string, unknown> | null | undefined) =>
  JSON.stringify(value ?? {}, null, 2);

const parseJsonObject = (value: string, label: string) => {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }
  const parsed = JSON.parse(trimmed);
  if (Array.isArray(parsed) || typeof parsed !== "object" || parsed === null) {
    throw new Error(`${label} must be a JSON object`);
  }
  return parsed;
};

const safeParseJson = (value: string, fallback: Record<string, unknown> = {}) => {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
};

const applyPatchToDraft = (base: ApiDraft, patchOps: { op: string; path: string; value: unknown }[]): ApiDraft => {
  const draftClone = JSON.parse(JSON.stringify(base)) as Record<string, unknown>;
  for (const op of patchOps ?? []) {
    if (op.op !== "replace") {
      continue;
    }
    const segments = op.path.split("/").filter(Boolean);
    if (segments.length === 0) {
      continue;
    }
    let cursor: Record<string, unknown> | unknown[] = draftClone;
    for (let idx = 0; idx < segments.length - 1; idx += 1) {
      const segment = segments[idx];
      const numericIndex = Number.parseInt(segment, 10);
      if (!Number.isNaN(numericIndex) && Number.isInteger(numericIndex)) {
        if (!Array.isArray(cursor)) {
          cursor = [];
        }
        if (!cursor[numericIndex]) {
          cursor[numericIndex] = {};
        }
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
      if (!Array.isArray(cursor)) {
        cursor = [];
      }
      cursor[numericLast] = op.value;
    } else {
      (cursor as Record<string, unknown>)[lastSegment] = op.value;
    }
  }
  return draftClone as ApiDraft;
};

const validateDraftShape = (draft: ApiDraft) => {
  if (!draft.api_name?.trim()) {
    return "draft.api_name 값이 필요합니다.";
  }
  if (!draft.method) {
    return "draft.method 값이 필요합니다.";
  }
  if (!draft.endpoint?.trim()) {
    return "draft.endpoint 값이 필요합니다.";
  }
  if (!draft.logic) {
    return "draft.logic 값이 필요합니다.";
  }
  if (draft.logic.type === "sql") {
    if (!draft.logic.query?.trim()) {
      return "draft.logic.query 값이 필요합니다.";
    }
  } else if (draft.logic.type === "http") {
    if (!draft.logic.spec?.url) {
      return "draft.logic.spec.url 값이 필요합니다.";
    }
    if (!draft.logic.spec?.method) {
      return "draft.logic.spec.method 값이 필요합니다.";
    }
  } else {
    return `지원하지 않는 logic.type 입니다: ${(draft.logic as { type?: string }).type}`;
  }
  return null;
};

const normalizeDraftPayload = (payload: unknown, baseDraft: ApiDraft) => {
  if (typeof payload !== "object" || payload === null) {
    return { ok: false, error: "JSON이 객체가 아닙니다." };
  }
  const obj = payload as Record<string, unknown>;
  if (obj.type !== "api_draft") {
    // Fallback: Check if it looks like a flat draft
    if (obj.api_name && (obj.endpoint || obj.logic)) {
      const draft = normalizeApiDraft(obj);
      const shapeError = validateDraftShape(draft);
      if (!shapeError) {
        return { ok: true, draft, notes: (obj.notes as string) ?? null };
      }
    }
    return { ok: false, error: "type=api_draft인 객체가 아닙니다." };
  }
  const mode = obj.mode;
  if (mode === "replace" || typeof mode === "undefined") {
    if (!obj.draft || typeof obj.draft !== "object") {
      return { ok: false, error: "draft 필드가 없습니다." };
    }
    const rawDraft = obj.draft as Record<string, unknown>;
    if (rawDraft?.logic && typeof rawDraft.logic === 'object' && rawDraft.logic !== null) {
      const logic = rawDraft.logic as Record<string, unknown>;
      if (logic.type === "http" && logic.request && !logic.spec) {
        logic.spec = logic.request;
      }
    }
    const draft = normalizeApiDraft(rawDraft);
    const shapeError = validateDraftShape(draft);
    if (shapeError) {
      return { ok: false, error: shapeError };
    }
    return { ok: true, draft, notes: (obj.notes as string) ?? null };
  }
  if (mode === "patch") {
    if (!Array.isArray(obj.patch)) {
      return { ok: false, error: "patch 배열이 필요합니다." };
    }
    const patched = applyPatchToDraft(baseDraft, obj.patch as { op: string; path: string; value: unknown }[]);
    if (patched?.logic?.type === "http" && 'request' in patched.logic && !('spec' in patched.logic)) {
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
    if (shapeError) {
      return { ok: false, error: shapeError };
    }
    return { ok: true, draft, notes: (obj.notes as string) ?? null };
  }
  return { ok: false, error: "mode는 replace 또는 patch여야 합니다." };
};

const stripCodeFences = (value: string) => {
  const match = value.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (match && match[1]) {
    return match[1].trim();
  }
  return value.trim();
};

const tryParseJson = (text: string) => {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
};

const extractJsonObjectFrom = (text: string, startIdx: number) => {
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

const extractJsonCandidates = (text: string) => {
  const candidates: string[] = [];
  let searchIdx = text.indexOf("{");
  while (searchIdx !== -1 && searchIdx < text.length) {
    try {
      const candidate = extractJsonObjectFrom(text, searchIdx);
      if (candidate.trim()) {
        candidates.push(candidate);
      }
      searchIdx = text.indexOf("{", searchIdx + candidate.length);
    } catch {
      searchIdx = text.indexOf("{", searchIdx + 1);
    }
  }
  return candidates;
};

const parseApiDraft = (text: string, baseDraft: ApiDraft) => {
  const rawCandidates = [stripCodeFences(text), text];
  let lastError: string | null = null;
  const tryNormalize = (payload: Record<string, unknown>) => {
    if (payload.type !== "api_draft") {
      return null;
    }
    const normalized = normalizeDraftPayload(payload, baseDraft);
    if (normalized.ok) {
      return normalized;
    }
    if (normalized.error) {
      lastError = normalized.error;
    }
    return null;
  };

  for (const candidate of rawCandidates) {
    if (!candidate.trim()) {
      continue;
    }
    const direct = tryParseJson(candidate);
    if (direct && typeof direct === "object" && direct !== null) {
      const normalized = tryNormalize(direct as Record<string, unknown>);
      if (normalized) {
        return normalized;
      }
    }
    const extractedCandidates = extractJsonCandidates(candidate);
    if (extractedCandidates.length === 0) {
      continue;
    }
    for (const extracted of extractedCandidates) {
      try {
        const parsed = JSON.parse(extracted);
        if (typeof parsed !== "object" || parsed === null) {
          continue;
        }
        const normalized = tryNormalize(parsed as Record<string, unknown>);
        if (normalized) {
          return normalized;
        }
      } catch {
        // ignore parse failures for individual candidates
      }
    }
  }
  return { ok: false, error: lastError ?? "JSON 객체를 추출할 수 없습니다." };
};

const normalizeApiDraft = (input: Record<string, unknown>): ApiDraft => {
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
    draft.logic = {
      type: "sql",
      query: String(logicInput?.query || ""),
    };
  }
  return draft;
};

const apiToDraft = (api: ApiDefinitionItem): ApiDraft => {
  const draft: ApiDraft = {
    api_name: api.api_name,
    method: api.method,
    endpoint: api.endpoint,
    description: api.description ?? "",
    tags: api.tags ?? [],
    params_schema: api.param_schema ?? {},
    runtime_policy: api.runtime_policy ?? {},
    is_active: api.is_active ?? true,
    logic: {
      type: "sql",
      query: "",
    },
  };

  if (api.logic_type === "http") {
    draft.logic = {
      type: "http",
      spec: safeParseJson(api.logic_body, { method: "GET", url: "" }),
    };
  } else {
    draft.logic = {
      type: "sql",
      query: api.logic_body,
    };
  }
  return draft;
};

const validateSql = (query: string) => {
  const errors: string[] = [];
  const warnings: string[] = [];
  const normalized = query.trim();
  if (!normalized) {
    errors.push("SQL 쿼리가 비어 있습니다.");
    return { ok: false, errors, warnings };
  }
  const sanitized = normalized.replace(/;+\s*$/, "");
  const statements = sanitized.split(";").map((statement) => statement.trim()).filter(Boolean);
  if (statements.length > 1) {
    errors.push("단일 SELECT 문만 허용합니다.");
  }
  const upperQuery = statements[0]?.toUpperCase() ?? "";
  if (!upperQuery.startsWith("SELECT")) {
    errors.push("SELECT 문만 허용됩니다.");
  }
  const bannedKeywords = ["DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE", "INSERT", "UPDATE", "DELETE"];
  for (const keyword of bannedKeywords) {
    const regex = new RegExp(`\\b${keyword}\\b`, "i");
    if (regex.test(normalized)) {
      errors.push(`${keyword} 키워드가 포함되어 있어 실행할 수 없습니다.`);
    }
  }
  if (normalized.includes(";") && statements.length === 1) {
    warnings.push("쿼리 끝에 세미콜론은 선택 사항입니다.");
  }
  return { ok: errors.length === 0, errors, warnings };
};

const validateApiDraft = (draft: ApiDraft) => {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (!draft.api_name.trim()) {
    errors.push("API 이름을 입력해야 합니다.");
  }
  if (!draft.endpoint.startsWith("/")) {
    errors.push("엔드포인트는 /로 시작해야 합니다.");
  }
  if (!["GET", "POST", "PUT", "DELETE"].includes(draft.method)) {
    errors.push("HTTP 메서드는 GET/POST/PUT/DELETE 중 하나여야 합니다.");
  }

  if (draft.logic.type === "sql") {
    if (!draft.logic.query.trim()) {
      errors.push("SQL 쿼리를 입력해야 합니다.");
    }
    const sqlResult = validateSql(draft.logic.query);
    errors.push(...sqlResult.errors);
    warnings.push(...sqlResult.warnings);
  } else if (draft.logic.type === "http") {
    if (!draft.logic.spec.url) {
      errors.push("HTTP Logic에 URL은 필수입니다.");
    }
  } else {
    errors.push(`지원하지 않는 로직 타입입니다: ${(draft.logic as { type?: string }).type}`);
  }

  return { ok: errors.length === 0, errors, warnings };
};

const computeDraftDiff = (draft: ApiDraft, baseline: ApiDraft) => {
  const differences: string[] = [];
  if (draft.api_name !== baseline.api_name) {
    differences.push(`Name: ${baseline.api_name || "<empty>"} → ${draft.api_name || "<empty>"}`);
  }
  if (draft.method !== baseline.method) {
    differences.push(`Method: ${baseline.method} → ${draft.method}`);
  }
  if (draft.endpoint !== baseline.endpoint) {
    differences.push(`Endpoint: ${baseline.endpoint || "<empty>"} → ${draft.endpoint || "<empty>"}`);
  }
  if (draft.description !== baseline.description) {
    differences.push(`Description changed`);
  }
  const dTags = draft.tags || [];
  const bTags = baseline.tags || [];
  if (dTags.join(",") !== bTags.join(",")) {
    differences.push(`Tags: ${bTags.join(", ") || "<empty>"} → ${dTags.join(", ") || "<empty>"}`);
  }
  if (draft.logic.type !== baseline.logic.type) {
    differences.push(`Logic type: ${baseline.logic.type} → ${draft.logic.type}`);
  }
  if (draft.logic.type === "sql" && baseline.logic.type === "sql") {
    if (draft.logic.query !== baseline.logic.query) {
      differences.push("Logic query updated");
    }
  } else if (draft.logic.type === "http" && baseline.logic.type === "http") {
    if (JSON.stringify(draft.logic.spec) !== JSON.stringify(baseline.logic.spec)) {
      differences.push("Logic HTTP spec updated");
    }
  } else {
    differences.push("Logic body updated");
  }

  return differences;
};

type ApiDraftBase = {
  api_name: string;
  method: "GET" | "POST" | "PUT" | "DELETE";
  endpoint: string;
  description: string;
  tags: string[];
  params_schema: Record<string, unknown>;
  runtime_policy: Record<string, unknown>;
  is_active: boolean;
};

type SqlLogic = {
  type: "sql";
  query: string;
  timeout_ms?: number;
};

type HttpLogic = {
  type: "http";
  spec: {
    method: string;
    url: string;
    headers?: Record<string, string>;
    params?: Record<string, unknown>;
    body?: unknown;
  };
  timeout_ms?: number;
};

type ApiDraft = ApiDraftBase & {
  logic: SqlLogic | HttpLogic;
  [key: string]: unknown;
};

type DraftStatus =
  | "idle"
  | "draft_ready"
  | "previewing"
  | "testing"
  | "applied"
  | "saved"
  | "outdated"
  | "error";

const DRAFT_STORAGE_PREFIX = "api-manager:draft:";
const FINAL_STORAGE_PREFIX = "api-manager:api:";

const tabOptions: { id: CenterTab; label: string }[] = [
  { id: "definition", label: "Definition" },
  { id: "logic", label: "Logic" },
  { id: "test", label: "Test" },
];

const draftStatusLabels: Record<DraftStatus, string> = {
  idle: "대기 중",
  draft_ready: "드래프트 준비됨",
  previewing: "미리보기",
  testing: "테스트 중",
  applied: "폼 적용됨",
  saved: "로컬 저장됨",
  outdated: "드래프트 오래됨",
  error: "오류 발생",
};

export default function ApiManagerPage() {
  const enableSystemApis = process.env.NEXT_PUBLIC_ENABLE_SYSTEM_APIS === "true";
  const [scope, setScope] = useState<ScopeType>(DEFAULT_SCOPE);
  const isSystemScope = enableSystemApis && scope === "system";
  const [apis, setApis] = useState<ApiDefinitionItem[]>([]);
  const [systemApis, setSystemApis] = useState<SystemApiItem[]>([]);
  const [systemError, setSystemError] = useState<string | null>(null);
  const [systemFetchStatus, setSystemFetchStatus] = useState<"idle" | "ok" | "error">("idle");
  const [systemFetchAt, setSystemFetchAt] = useState<string | null>(null);
  const [localApis, setLocalApis] = useState<ApiDefinitionItem[]>([]);
  const skipAutoSelectRef = useRef(false);
  const skipResetRef = useRef(false);
  const [systemView, setSystemView] = useState<SystemView>("discovered");
  const [discoveredEndpoints, setDiscoveredEndpoints] = useState<DiscoveredEndpoint[]>([]);
  const [discoveredError, setDiscoveredError] = useState<string | null>(null);
  const [discoveredFetchStatus, setDiscoveredFetchStatus] = useState<"idle" | "ok" | "error">("idle");
  const [discoveredFetchAt, setDiscoveredFetchAt] = useState<string | null>(null);
  const [discoveredSearchTerm, setDiscoveredSearchTerm] = useState("");
  const [selectedDiscovered, setSelectedDiscovered] = useState<DiscoveredEndpoint | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [systemSearchTerm, setSystemSearchTerm] = useState("");
  const [draftApi, setDraftApi] = useState<ApiDraft | null>(null);
  const [draftStatus, setDraftStatus] = useState<DraftStatus>("idle");
  const [draftNotes, setDraftNotes] = useState<string | null>(null);
  const [draftErrors, setDraftErrors] = useState<string[]>([]);
  const [draftWarnings, setDraftWarnings] = useState<string[]>([]);
  const [draftTestOk, setDraftTestOk] = useState<boolean | null>(null);
  const [previewJson, setPreviewJson] = useState<string | null>(null);
  const [previewSummary, setPreviewSummary] = useState<string | null>(null);
  const [draftDiff, setDraftDiff] = useState<string[] | null>(null);
  const [lastAssistantRaw, setLastAssistantRaw] = useState("");
  const [lastParseStatus, setLastParseStatus] = useState<"idle" | "success" | "fail">("idle");
  const [lastParseError, setLastParseError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<CenterTab>(DEFAULT_TAB);
  const [definitionDraft, setDefinitionDraft] = useState({
    api_name: "",
    method: "GET",
    endpoint: "",
    description: "",
    tags: "",
    is_active: true,
    created_by: "",
  });
  const [logicBody, setLogicBody] = useState("");
  const [logicType, setLogicType] = useState<LogicType>("sql");
  const [scriptLanguage, setScriptLanguage] = useState<"python" | "javascript">("python");
  const [paramSchemaText, setParamSchemaText] = useState("{}");
  const [runtimePolicyText, setRuntimePolicyText] = useState("{}");
  const [httpSpec, setHttpSpec] = useState({
    url: "",
    method: "GET",
    headers: "{}",
    body: "{}",
    params: "{}",
  });
  const [testParams, setTestParams] = useState("{}");
  const [testInput, setTestInput] = useState("{}");
  const [testLimit, setTestLimit] = useState("200");
  const [executedBy, setExecutedBy] = useState("ops-builder");
  const [executionResult, setExecutionResult] = useState<ExecuteResult | null>(null);
  const [workflowResult, setWorkflowResult] = useState<WorkflowExecuteResult | null>(null);
  const [execLogs, setExecLogs] = useState<ExecLogEntry[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);
  const [showJsonResult, setShowJsonResult] = useState(false);
  const [showLogicResult, setShowLogicResult] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [logicFilter, setLogicFilter] = useState<"all" | LogicType>("all");
  const [formBaselineSnapshot, setFormBaselineSnapshot] = useState<string | null>(null);
  const [appliedDraftSnapshot, setAppliedDraftSnapshot] = useState<string | null>(null);
  const [saveTarget, setSaveTarget] = useState<"server" | "local" | null>(null);
  const [lastSaveError, setLastSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (logicType === "http") {
      try {
        const spec = {
          url: httpSpec.url,
          method: httpSpec.method,
          headers: JSON.parse(httpSpec.headers || "{}"),
          body: JSON.parse(httpSpec.body || "{}"),
          params: JSON.parse(httpSpec.params || "{}"),
        };
        setLogicBody(JSON.stringify(spec, null, 2));
      } catch (error) {
        console.error("Error creating http logic body from spec:", error);
      }
    }
  }, [httpSpec, logicType]);

  useEffect(() => {
    if (!enableSystemApis && scope === "system") {
      setScope("custom");
    }
  }, [enableSystemApis, scope]);

  const selectedApi = useMemo(() => {
    if (scope === "system" && enableSystemApis) {
      return systemApis.find((api) => api.api_id === selectedId) ?? null;
    }
    const found = apis.find((api) => api.api_id === selectedId) || localApis.find((api) => api.api_id === selectedId);
    if (found) return found;

    if (selectedId === "applied-draft-temp" && draftApi) {
      return buildTemporaryApiFromDraft(draftApi);
    }
    return null;
  }, [apis, systemApis, localApis, selectedId, scope, enableSystemApis, draftApi]);

  const discoveredConstraintLines = useMemo(() => {
    if (!selectedDiscovered) {
      return [];
    }
    return selectedDiscovered.description
      ? selectedDiscovered.description
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
      : [];
  }, [selectedDiscovered]);

  const buildDraftFromForm = useCallback((): ApiDraft => {
    const draft: ApiDraft = {
      api_name: definitionDraft.api_name,
      method: definitionDraft.method as ApiDraft["method"],
      endpoint: definitionDraft.endpoint,
      description: definitionDraft.description,
      tags: parseTags(definitionDraft.tags),
      params_schema: safeParseJson(paramSchemaText),
      runtime_policy: safeParseJson(runtimePolicyText),
      is_active: definitionDraft.is_active,
      logic: {
        type: "sql",
        query: "",
      },
    };

    if (logicType === "http") {
      draft.logic = {
        type: "http",
        spec: {
          method: httpSpec.method,
          url: httpSpec.url,
          headers: safeParseJson(httpSpec.headers),
          params: safeParseJson(httpSpec.params),
          body: safeParseJson(httpSpec.body),
        },
      };
    } else {
      draft.logic = {
        type: "sql",
        query: logicBody,
      };
    }

    return draft;
  }, [definitionDraft, paramSchemaText, runtimePolicyText, logicType, httpSpec, logicBody]);

  const buildSavePayload = useCallback(() => {
    if (isSystemScope) {
      setStatusMessage("System APIs are read-only. Import to Custom to edit.");
      return null;
    }
    if (scope === "custom" && !(logicBody || "").trim()) {
      setStatusMessage("Logic body is required for custom APIs.");
      return null;
    }
    const parseOrFail = (text: string, label: string) => {
      try {
        return parseJsonObject(text, label);
      } catch (error) {
        setStatusMessage(error instanceof Error ? error.message : `Invalid ${label}`);
        return null;
      }
    };
    const parsedParamSchema = parseOrFail(paramSchemaText, "param schema");
    if (parsedParamSchema === null) return null;
    const parsedRuntimePolicy = parseOrFail(runtimePolicyText, "runtime policy");
    if (parsedRuntimePolicy === null) return null;
    let logicSpecPayload: Record<string, unknown> = {};
    if (logicType === "workflow") {
      const parsedLogicSpec = parseOrFail(logicBody, "workflow spec");
      if (parsedLogicSpec === null) return null;
      logicSpecPayload = parsedLogicSpec;
    } else if (logicType === "script") {
      logicSpecPayload = { language: scriptLanguage };
    } else if (logicType === "python") {
      logicSpecPayload = { language: "python" };
    } else if (logicType === "http") {
      logicSpecPayload = {};
    }
    return {
      api_name: (definitionDraft.api_name || "").trim(),
      api_type: scope,
      method: (definitionDraft.method || "GET").toUpperCase(),
      endpoint: (definitionDraft.endpoint || "").trim(),
      description: (definitionDraft.description || "").trim() || null,
      tags: parseTags(definitionDraft.tags || ""),
      logic_type: logicType,
      logic_body: (logicBody || "").trim(),
      param_schema: parsedParamSchema,
      runtime_policy: parsedRuntimePolicy,
      logic_spec: logicSpecPayload,
      is_active: definitionDraft.is_active,
      created_by: definitionDraft.created_by || "ops-builder",
    };
  }, [
    isSystemScope,
    logicBody,
    paramSchemaText,
    runtimePolicyText,
    logicType,
    scriptLanguage,
    definitionDraft,
    scope,
  ]);

  const buildFormSnapshot = useCallback(() => {
    return JSON.stringify(buildDraftFromForm());
  }, [buildDraftFromForm]);

  const apiBaseUrl = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

  const saveApiToServer = useCallback(
    async (payload: Record<string, unknown>, forceCreate = false) => {
      const isUpdating = selectedApi && selectedApi.api_id !== "applied-draft-temp" && !forceCreate;
      const target = isUpdating
        ? `${apiBaseUrl}/api-manager/apis/${selectedApi.api_id}`
        : `${apiBaseUrl}/api-manager/apis`;
      const method = isUpdating ? "PUT" : "POST";
      try {
        const response = await fetch(target, {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
          return { ok: false, error: result?.message ?? "Failed to save API definition", details: result };
        }
        return { ok: true, data: result?.data?.api ?? null };
      } catch (error) {
        return { ok: false, error: error instanceof Error ? error.message : "Network error", details: error };
      }
    },
    [apiBaseUrl, selectedApi]
  );
  const draftStorageId = selectedId === "applied-draft-temp" ? "new" : (selectedId ?? "new");
  const finalStorageId = selectedId === "applied-draft-temp"
    ? (definitionDraft.endpoint || "new")
    : (selectedId ?? (definitionDraft.endpoint || "new"));

  const getLocalSystemApis = useCallback(() => {
    if (typeof window === "undefined") {
      return [] as SystemApiItem[];
    }
    const items: SystemApiItem[] = [];
    for (let i = 0; i < window.localStorage.length; i += 1) {
      const key = window.localStorage.key(i);
      if (!key || !key.startsWith(FINAL_STORAGE_PREFIX)) {
        continue;
      }
      const raw = window.localStorage.getItem(key);
      if (!raw) {
        continue;
      }
      try {
        const payload = JSON.parse(raw) as Record<string, unknown>;
        const apiName = (payload.api_name as string) ?? "Local API";
        const endpoint = (payload.endpoint as string) ?? "";
        const apiId = `local:${endpoint || apiName}`;
        items.push({
          api_id: apiId,
          api_name: apiName,
          api_type: "system",
          method: (payload.method as "GET" | "POST") ?? "GET",
          endpoint,
          logic_type: (payload.logic_type as LogicType) ?? "sql",
          logic_body: (payload.logic_body as string) ?? "",
          description: (payload.description as string) ?? null,
          tags: (payload.tags as string[]) ?? [],
          is_active: true,
          created_by: "local",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          param_schema: (payload.param_schema as Record<string, unknown>) ?? {},
          runtime_policy: (payload.runtime_policy as Record<string, unknown>) ?? {},
          logic_spec: (payload.logic_spec as Record<string, unknown>) ?? {},
          source: "local",
        });
      } catch {
        // ignore malformed local entries
      }
    }
    return items;
  }, []);

  const loadApis = useCallback(
    async (preferredId?: string) => {
      if (scope === "system" && enableSystemApis) {
        setSystemError(null);
        setSystemFetchStatus("idle");
        setSystemFetchAt(new Date().toISOString());
        try {
          const response = await fetch(buildApiUrl("/api-manager/apis?scope=system", apiBaseUrl));
          if (!response.ok) {
            throw new Error("Failed to load system APIs");
          }
          const payload = await response.json();
          const items: Record<string, unknown>[] = (payload.data?.apis ?? []) as Record<string, unknown>[];
          const normalized: ApiDefinitionItem[] = items.map((item) => ({
            api_id: item.id as string,
            api_name: item.name as string,
            api_type: item.scope as ScopeType,
            method: item.method as "GET" | "POST" | "PUT" | "DELETE",
            endpoint: item.path as string,
            logic_type: (item.mode || "sql") as LogicType,
            logic_body: item.logic as string,
            description: item.description as string | null,
            tags: item.tags as string[],
            is_active: item.is_enabled as boolean,
            created_by: null,
            created_at: (item.created_at as string) || new Date().toISOString(),
            updated_at: (item.updated_at as string) || new Date().toISOString(),
            param_schema: {},
            runtime_policy: {},
            logic_spec: {},
            source: "server" as const,
          }));
          setSystemApis(normalized as SystemApiItem[]);
          setSystemFetchStatus("ok");
          setSelectedId((prev): string | null => {
            if (preferredId) {
              return preferredId;
            }
            if (prev && normalized.some((item) => item.api_id === prev)) {
              return prev;
            }
            return normalized[0]?.api_id ?? null;
          });
        } catch (error) {
          console.error("Unable to fetch system APIs", error);
          const message = error instanceof Error ? error.message : "Failed to load system APIs";
          setSystemError(message);
          setSystemFetchStatus("error");
          const localItems = getLocalSystemApis();
          setSystemApis(localItems);
          setSelectedId((prev): string | null => {
            if (preferredId) {
              return preferredId;
            }
            if (prev && localItems.some((item) => item.api_id === prev)) {
              return prev;
            }
            return localItems[0]?.api_id ?? null;
          });
        }
        return;
      }
      try {
        const params = new URLSearchParams();
        if (scope) {
          params.set("scope", scope);
        }
        const queryString = params.toString();
        const response = await fetch(buildApiUrl(`/api-manager/apis${queryString ? `?${queryString}` : ""}`, apiBaseUrl));
        if (!response.ok) {
          throw new Error("Failed to load API definitions");
        }
        const payload = await response.json();
        const items: Record<string, unknown>[] = (payload.data?.apis ?? []) as Record<string, unknown>[];
        const normalized: SystemApiItem[] = items.map((item) => ({
          api_id: item.id as string,
          api_name: item.name as string,
          api_type: item.scope as ScopeType,
          method: item.method as "GET" | "POST" | "PUT" | "DELETE",
          endpoint: item.path as string,
          logic_type: (item.mode || "sql") as LogicType,
          logic_body: item.logic as string,
          description: item.description as string | null,
          tags: item.tags as string[],
          is_active: item.is_enabled as boolean,
          created_by: null,
          created_at: (item.created_at as string) || new Date().toISOString(),
          updated_at: (item.updated_at as string) || new Date().toISOString(),
          param_schema: {},
          runtime_policy: {},
          logic_spec: {},
          source: "server" as const,
        }));
        setApis(normalized);
        if (skipAutoSelectRef.current) {
          skipAutoSelectRef.current = false;
          return;
        }
          setSelectedId((prev): string | null => {
            if (preferredId) {
              return preferredId;
            }
            if (prev && items.some((item) => item.api_id === prev)) {
              return prev;
            }
            return (items[0]?.api_id as string | undefined) || null;
          });
      } catch (error) {
        console.error("Unable to fetch APIs", error);
        setApis([]);
        setSelectedId(null);
      }
    },
    [apiBaseUrl, scope, enableSystemApis, getLocalSystemApis]
  );

  const loadLocalCustomApis = useCallback(() => {
    if (typeof window === "undefined") return;
    const items: ApiDefinitionItem[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key?.startsWith(FINAL_STORAGE_PREFIX)) {
        try {
          const raw = window.localStorage.getItem(key);
          if (raw) {
            const parsed = JSON.parse(raw);
            // It might be a partial draft or a full API definition depending on how it was saved
            // Ensure basic fields are present to treat as a "local" record
            if (parsed.endpoint && parsed.api_name) {
              const localId = key.replace(FINAL_STORAGE_PREFIX, "");
              items.push({
                ...parsed,
                api_id: parsed.api_id || `local-${localId}`,
                updated_at: parsed.updated_at || new Date().toISOString(),
                created_at: parsed.created_at || new Date().toISOString(),
                source: "local"
              });
            }
          }
        } catch (e) {
          console.error("Failed to parse local API", e);
        }
      }
    }
    setLocalApis(items);
  }, []);

  useEffect(() => {
    if (draftStatus !== "applied" && draftStatus !== "outdated") {
      setLocalApis((prev) => prev.filter((api) => api.api_id !== "applied-draft-temp"));
    }
  }, [draftStatus]);

  useEffect(() => {
    loadLocalCustomApis();
  }, [loadLocalCustomApis]);

  const loadDiscoveredEndpoints = useCallback(async () => {
    if (!isSystemScope) {
      return;
    }
    setDiscoveredError(null);
    setDiscoveredFetchStatus("idle");
    setDiscoveredFetchAt(new Date().toISOString());
    try {
      // Note: Currently, there is no distinct /api-manager/system/endpoints endpoint
      // System APIs are fetched via /api-manager/apis?scope=system
      // For now, we'll show an empty list or fetch from the main API list
      setDiscoveredEndpoints([]);
      setDiscoveredFetchStatus("ok");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load discovered endpoints";
      setDiscoveredError(message);
      setDiscoveredFetchStatus("error");
      setDiscoveredEndpoints([]);
    }
  }, [isSystemScope]);

  const fetchExecLogs = useCallback(async () => {
    if (!selectedId || selectedId === "applied-draft-temp" || selectedId.startsWith("local") || selectedId.startsWith("system:")) {
      setExecLogs([]);
      return;
    }
    setLogsLoading(true);
    try {
      const response = await fetch(buildApiUrl(`/api-manager/apis/${selectedId}/execution-logs?limit=20`, apiBaseUrl));
      if (!response.ok) {
        throw new Error("Failed to load execution logs");
      }
      const payload = await response.json();
      setExecLogs(payload.data?.logs ?? []);
    } catch {
      // Silently fail - execution logs are optional
      setExecLogs([]);
    } finally {
      setLogsLoading(false);
    }
  }, [apiBaseUrl, selectedId]);

  useEffect(() => {
    setSelectedId(null);
    loadApis();
  }, [loadApis]);

  useEffect(() => {
    if (isSystemScope && systemView === "discovered") {
      loadDiscoveredEndpoints();
    }
  }, [isSystemScope, systemView, loadDiscoveredEndpoints]);

  useEffect(() => {
    if (selectedId === "applied-draft-temp" && draftApi) {
      return;
    }
    const key = `${DRAFT_STORAGE_PREFIX}${draftStorageId}`;
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      setDraftApi(null);
      setDraftStatus("idle");
      setDraftNotes(null);
      setPreviewJson(null);
      setPreviewSummary(null);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as ApiDraft;
      setDraftApi(parsed);
      setDraftStatus("draft_ready");
      setDraftNotes("미적용 드래프트가 있습니다.");
      setDraftTestOk(null);
      setPreviewJson(JSON.stringify(parsed, null, 2));
      setPreviewSummary(`${parsed.method} ${parsed.endpoint}`);
    } catch {
      window.localStorage.removeItem(key);
      setDraftApi(null);
      setDraftStatus("idle");
    }
  }, [draftStorageId, selectedId, draftApi]);

  useEffect(() => {
    const key = `${DRAFT_STORAGE_PREFIX}${draftStorageId}`;
    if (!draftApi) {
      window.localStorage.removeItem(key);
      return;
    }
    window.localStorage.setItem(key, JSON.stringify(draftApi));
  }, [draftApi, draftStorageId]);

  useEffect(() => {
    const key = `${FINAL_STORAGE_PREFIX}${finalStorageId}`;
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return;
    }
    try {
      const parsed = JSON.parse(raw) as ApiDraft;
      applyFinalToForm(parsed);
      setFormBaselineSnapshot(JSON.stringify(parsed));
      setAppliedDraftSnapshot(null);
      setStatusMessage("로컬 저장된 API 정의를 불러왔습니다.");
    } catch {
      window.localStorage.removeItem(key);
    }
  }, [finalStorageId]);

  useEffect(() => {
    if (!draftApi) {
      setDraftDiff(null);
      return;
    }
    const baseline = selectedApi ? apiToDraft(selectedApi) : buildDraftFromForm();
    const diffSummary = computeDraftDiff(draftApi, baseline);
    setDraftDiff(diffSummary.length ? diffSummary : ["변경 사항이 없습니다."]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftApi, selectedApi]);

  useEffect(() => {
    const currentSnapshot = buildFormSnapshot();
    if (formBaselineSnapshot === null) {
      setFormBaselineSnapshot(currentSnapshot);
      return;
    }
    if (draftApi && appliedDraftSnapshot && currentSnapshot !== appliedDraftSnapshot) {
      setDraftStatus("outdated");
      setDraftNotes("폼이 변경되어 드래프트가 오래되었습니다.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formBaselineSnapshot, draftApi, appliedDraftSnapshot]);

  useEffect(() => {
    if (skipResetRef.current) {
      skipResetRef.current = false;
      return;
    }
    if (!selectedApi) {
      setDefinitionDraft({
        api_name: "",
        method: "GET",
        endpoint: "",
        description: "",
        tags: "",
        is_active: true,
        created_by: "",
      });
      setLogicBody("");
      setLogicType("sql");
      setHttpSpec({ url: "", method: "GET", headers: "{}", body: "{}", params: "{}" });
      setParamSchemaText("{}");
      setRuntimePolicyText("{}");
      setActiveTab(DEFAULT_TAB);
      setStatusMessage(null);
      setExecutionResult(null);
      setTestError(null);
      setShowJsonResult(false);
      setExecLogs([]);
      setWorkflowResult(null);
      setTestInput("{}");
      setFormBaselineSnapshot(JSON.stringify(buildDraftFromForm()));
      return;
    }
    setDefinitionDraft({
      api_name: selectedApi.api_name,
      method: selectedApi.method,
      endpoint: selectedApi.endpoint,
      description: selectedApi.description ?? "",
      tags: (selectedApi.tags || []).join(", "),
      is_active: selectedApi.is_active,
      created_by: selectedApi.created_by ?? "",
    });
    setLogicBody(selectedApi.logic_body);
    setLogicType(selectedApi.logic_type);

    if (selectedApi.logic_type === "http") {
      try {
        const spec = JSON.parse(selectedApi.logic_body || "{}");
        setHttpSpec({
          url: spec.url || "",
          method: spec.method || "GET",
          headers: JSON.stringify(spec.headers || {}, null, 2),
          body: JSON.stringify(spec.body || {}, null, 2),
          params: JSON.stringify(spec.params || {}, null, 2),
        });
      } catch {
        // Reset to default if parsing fails
        setHttpSpec({ url: "", method: "GET", headers: "{}", body: "{}", params: "{}" });
      }
    }

    setParamSchemaText(formatJson(selectedApi.param_schema));
    setRuntimePolicyText(formatJson(selectedApi.runtime_policy));
    const specLanguage = (selectedApi.logic_spec?.language ?? "") as string;
    setScriptLanguage(specLanguage === "javascript" ? "javascript" : "python");
    setActiveTab(DEFAULT_TAB);
    setStatusMessage(buildStatusMessage(selectedApi));
    setExecutionResult(null);
    setTestError(null);
    setShowJsonResult(false);
    setExecutedBy(selectedApi.created_by ?? "ops-builder");
    setWorkflowResult(null);
    setTestInput("{}");
    fetchExecLogs();
    const baseline = apiToDraft(selectedApi);
    setFormBaselineSnapshot(JSON.stringify(baseline));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedApi, fetchExecLogs]);

  const filteredApis = useMemo(() => {
    // Combine server-fetched APIs and local-stored APIs
    const merged = [...apis];
    for (const local of localApis) {
      if (!merged.find(a => a.api_id === local.api_id || (a.endpoint === local.endpoint && a.method === local.method))) {
        merged.push(local);
      }
    }

    // If a draft is applied but not yet in the list, unshift a temporary "Draft" entry
    if ((draftStatus === "applied" || draftStatus === "outdated") && draftApi) {
      const alreadyExists = merged.find(a => a.endpoint === draftApi.endpoint && a.method === draftApi.method);
      if (!alreadyExists) {
        merged.unshift(buildTemporaryApiFromDraft(draftApi));
      }
    }

    let result = merged;
    if (logicFilter !== "all") {
      result = result.filter((api) => api.logic_type === logicFilter);
    }
    if (!searchTerm.trim()) {
      return result;
    }
    const lower = searchTerm.toLowerCase();
    return result.filter(
      (api) =>
        api.api_name.toLowerCase().includes(lower) ||
        api.endpoint.toLowerCase().includes(lower) ||
        api.method.toLowerCase().includes(lower) ||
        (api.tags || []).join(",").toLowerCase().includes(lower)
    );
  }, [apis, localApis, draftStatus, draftApi, searchTerm, logicFilter]);

  const filteredSystemApis = useMemo(() => {
    if (!systemSearchTerm.trim()) {
      return systemApis;
    }
    const lower = systemSearchTerm.toLowerCase();
    return systemApis.filter(
      (api) =>
        api.api_name.toLowerCase().includes(lower) ||
        api.endpoint.toLowerCase().includes(lower) ||
        api.method.toLowerCase().includes(lower) ||
        (api.tags || []).join(",").toLowerCase().includes(lower)
    );
  }, [systemApis, systemSearchTerm]);

  const filteredDiscoveredEndpoints = useMemo(() => {
    if (!discoveredSearchTerm.trim()) {
      return discoveredEndpoints;
    }
    const lower = discoveredSearchTerm.toLowerCase();
    return discoveredEndpoints.filter((endpoint) => {
      const tags = endpoint.tags?.join(",") ?? "";
      return (
        endpoint.path.toLowerCase().includes(lower) ||
        endpoint.method.toLowerCase().includes(lower) ||
        (endpoint.summary ?? "").toLowerCase().includes(lower) ||
        tags.toLowerCase().includes(lower)
      );
    });
  }, [discoveredEndpoints, discoveredSearchTerm]);

  const handleSave = async () => {
    const payload = buildSavePayload();
    if (!payload) {
      return;
    }
    // If endpoint is different from selected, force create (POST instead of PUT)
    // If we are currently in virtual draft mode or a local-only mode, we must forceCreate on the server
    const isVirtual = selectedId === "applied-draft-temp" || (selectedApi && selectedApi.api_id.startsWith("local-"));
    const isEndpointDifferent = selectedApi && !isVirtual && payload.endpoint !== selectedApi.endpoint;
    const isLogicTypeDifferent = selectedApi && !isVirtual && payload.logic_type !== selectedApi.logic_type;
    const forceCreate = isVirtual || Boolean(isEndpointDifferent || isLogicTypeDifferent);

    setIsSaving(true);
    setSaveTarget(null);
    setLastSaveError(null);
    try {
      const result = await saveApiToServer(payload, forceCreate);
      if (!result.ok) {
        setLastSaveError(result.error ?? "Failed to save API definition");
        setStatusMessage(result.error ?? "Save failed. 확인 로그를 참고하세요.");
        return;
      }
      const saved = result.data as ApiDefinitionItem | null;
      setStatusMessage(forceCreate || !selectedApi ? "API created" : "API updated");
      setSaveTarget("server");
      if (saved?.api_id) {
        setSelectedId(saved.api_id);
        await loadApis(saved.api_id);
      } else {
        await loadApis(selectedId ?? undefined);
      }
      loadLocalCustomApis();
    } finally {
      setIsSaving(false);
    }
  };

  const handlePreviewDraft = () => {
    if (!draftApi) {
      setDraftErrors(["AI 드래프트가 없습니다."]);
      return;
    }
    setDraftStatus("previewing");
    setPreviewJson(JSON.stringify(draftApi, null, 2));
    setPreviewSummary(`${draftApi.method} ${draftApi.endpoint}`);
    setDraftNotes("드래프트를 미리보기로 렌더링합니다.");
  };

  const handleTestDraft = async () => {
    if (!draftApi) {
      setDraftErrors(["AI 드래프트가 없습니다."]);
      return;
    }
    const validation = validateApiDraft(draftApi);
    setDraftErrors(validation.errors);
    setDraftWarnings(validation.warnings);

    if (!validation.ok) {
      setDraftNotes("규격 테스트 실패 (Dry-run 생략)");
      setDraftTestOk(false);
      setDraftStatus("error");
      return;
    }

    setDraftStatus("testing");
    setDraftNotes("실제 로직 테스트 중 (Dry-run)...");

    try {
      const bodyValue = draftApi.logic.type === "sql"
        ? draftApi.logic.query
        : JSON.stringify(draftApi.logic.spec);

      const response = await fetch(buildApiUrl("/api-manager/dry-run", apiBaseUrl), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          logic_type: draftApi.logic.type,
          logic_body: bodyValue,
          params: draftApi.params_schema || {},
          runtime_policy: draftApi.runtime_policy || { allow_runtime: true }, // Ensure it can run during test
        })
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body?.message || body?.detail || "Dry-run failed");
      }

      setExecutionResult(body.data.result);
      setShowLogicResult(true);

      setDraftNotes("실제 로직 테스트 성공! 데이터를 확인하세요.");
      setDraftTestOk(true);
      setDraftStatus("draft_ready");
    } catch (err) {
      setDraftErrors([err instanceof Error ? err.message : "네트워크 오류"]);
      setDraftNotes("실제 로직 테스트 실패");
      setDraftTestOk(false);
      setDraftStatus("error");
    }
  };

  const applyFinalToForm = (draft: ApiDraft) => {
    setDefinitionDraft((prev) => ({
      ...prev,
      api_name: draft.api_name,
      method: draft.method,
      endpoint: draft.endpoint,
      description: draft.description ?? "",
      tags: (draft.tags || []).join(", "),
      is_active: typeof draft.is_active === "boolean" ? draft.is_active : true,
    }));
    setParamSchemaText(JSON.stringify(draft.params_schema || {}, null, 2));
    setRuntimePolicyText(JSON.stringify(draft.runtime_policy || {}, null, 2));

    if (draft.logic.type === "http") {
      setLogicType("http");
      const spec = draft.logic.spec;
      setHttpSpec({
        url: spec.url || "",
        method: spec.method || "GET",
        headers: JSON.stringify(spec.headers || {}, null, 2),
        body: JSON.stringify(spec.body || {}, null, 2),
        params: JSON.stringify(spec.params || {}, null, 2),
      });
      // logicBody will be updated by the useEffect for httpSpec
    } else {
      setLogicType("sql");
      setLogicBody(draft.logic.query);
    }
  };

  const applyDraftToForm = (draft: ApiDraft) => {
    // Fill the form fields
    applyFinalToForm(draft);
    setDraftStatus("applied");

    // Switch to virtual draft mode so it appears in the list as [NEW]
    skipResetRef.current = true;
    setSelectedId("applied-draft-temp");

    setDraftNotes("드래프트가 폼에 적용되었습니다. 저장 전입니다.");
    setStatusMessage("Draft applied. 리스트에서 [NEW] 항목을 확인하세요.");
    // Explicitly normalize before snapshotting to guarantee key order matches buildDraftFromForm
    setAppliedDraftSnapshot(JSON.stringify(normalizeApiDraft(draft)));
    setLocalApis((prev) => {
      const tempEntry = buildTemporaryApiFromDraft(draft);
      return [tempEntry, ...prev.filter((api) => api.api_id !== "applied-draft-temp")];
    });
  };

  const handleApplyDraft = () => {
    if (!draftApi) {
      setDraftErrors(["AI 드래프트가 없습니다."]);
      return;
    }
    applyDraftToForm(draftApi);
    setDraftErrors([]);
    setDraftWarnings([]);
  };

  const handleSaveLocalDraft = () => {
    if (!draftApi) {
      setDraftErrors(["AI 드래프트가 없습니다."]);
      return;
    }
    if (draftTestOk !== true) {
      setDraftErrors(["테스트를 통과한 뒤 저장할 수 있습니다."]);
      return;
    }
    const finalPayload = buildSavePayload();
    if (!finalPayload) return;
    const storageKey = `${FINAL_STORAGE_PREFIX}${finalStorageId}`;
    setIsSaving(true);
    setSaveTarget(null);
    setLastSaveError(null);

    const isVirtual = selectedId === "applied-draft-temp" || (selectedApi && selectedApi.api_id.startsWith("local-"));
    const forceCreate = isVirtual || (selectedApi ? finalPayload.endpoint !== selectedApi.endpoint : false);

    saveApiWithFallback({
      payload: finalPayload,
      saveApiToServer: (p: Record<string, unknown>) => saveApiToServer(p, forceCreate),
      storage: window.localStorage,
      storageKey,
    })
      .then(async (result) => {
        setSaveTarget(result.target as "server" | "local");
        if (result.target === "server") {
          setStatusMessage("Saved to server.");
          setDraftNotes("서버에 저장되었습니다.");
          const saved = result.data as ApiDefinitionItem | null;
          if (saved?.api_id) {
            setSelectedId(saved.api_id);
            await loadApis(saved.api_id);
          } else {
            await loadApis(selectedId ?? undefined);
          }
          window.localStorage.removeItem(storageKey);
        } else {
          setStatusMessage("Saved locally (server unavailable).");
          setDraftNotes("서버 저장 실패로 로컬에 저장했습니다.");
          loadLocalCustomApis();
        }
        setDraftApi(null);
        setDraftStatus("saved");
        setDraftTestOk(null);
          setFormBaselineSnapshot(JSON.stringify(finalPayload));
        setAppliedDraftSnapshot(null);
        const draftKey = `${DRAFT_STORAGE_PREFIX}${draftStorageId}`;
        window.localStorage.removeItem(draftKey);
      })
      .catch((error) => {
        const message = error instanceof Error ? error.message : "Save failed";
        setLastSaveError(message);
        setStatusMessage(message);
      })
      .finally(() => {
        setIsSaving(false);
      });
  };

  const handleNew = useCallback(() => {
    setSelectedId(null);
    setDraftApi(null);
    setDraftStatus("idle");
    setAppliedDraftSnapshot(null);
    setStatusMessage("새 API 정의를 시작합니다.");
    setDefinitionDraft({
      api_name: "",
      method: "GET",
      endpoint: "",
      description: "",
      tags: "",
      is_active: true,
      created_by: "",
    });
    setLogicBody("");
    setLogicType("sql");
    setHttpSpec({ url: "", method: "GET", headers: "{}", body: "{}", params: "{}" });
    setScriptLanguage("python");
    setParamSchemaText("{}");
    setRuntimePolicyText("{}");
    setStatusMessage("새 API 정의를 작성하세요.");
    setFormBaselineSnapshot(JSON.stringify(buildDraftFromForm()));
    setAppliedDraftSnapshot(null);
  }, [buildDraftFromForm]);

  const handleImportDiscoveredEndpoint = useCallback((endpoint: DiscoveredEndpoint) => {
    const draft: ApiDraft = {
      api_name: endpoint.summary?.toString().trim() || `Imported ${endpoint.method} ${endpoint.path}`,
      method: endpoint.method === "POST" ? "POST" : "GET",
      endpoint: `/api-manager/imported${endpoint.path}`,
      description: `Imported from discovered endpoint ${endpoint.method} ${endpoint.path}`,
      tags: endpoint.tags ?? [],
      params_schema: {
        parameters: endpoint.parameters ?? [],
        requestBody: endpoint.requestBody ?? null,
        responses: endpoint.responses ?? null,
        source: "discovered",
      },
      runtime_policy: {},
      is_active: true,
      logic: {
        type: "sql",
        query: "SELECT 1",
      },
    };
    skipAutoSelectRef.current = true;
    setScope("custom");
    setSelectedId(null);
    applyFinalToForm(draft);
    setDefinitionDraft((prev) => ({
      ...prev,
      created_by: "imported",
    }));
    setStatusMessage("System API imported into Custom (unsaved).");
    setFormBaselineSnapshot(JSON.stringify(draft));
    setAppliedDraftSnapshot(null);
    setDraftApi(null);
    setDraftStatus("idle");
    setDraftNotes(null);
  }, []);

  const buildDraftFromDiscovered = useCallback((endpoint: DiscoveredEndpoint): ApiDraft => {
    return {
      api_name: endpoint.summary?.toString().trim() || `${endpoint.method} ${endpoint.path}`,
      method: endpoint.method === "POST" ? "POST" : "GET",
      endpoint: endpoint.path,
      description: endpoint.description?.toString() ?? "",
      tags: endpoint.tags ?? [],
      params_schema: {
        parameters: endpoint.parameters ?? [],
        requestBody: endpoint.requestBody ?? null,
        responses: endpoint.responses ?? null,
        source: "discovered",
      },
      logic: {
        type: "sql",
        query: "SELECT 1",
      },
      runtime_policy: {},
      is_active: true,
    };
  }, []);

  const handleExecute = async () => {
    if (!selectedId || !selectedApi) {
      setTestError("선택된 API가 없습니다.");
      return;
    }
    if (selectedApi.logic_type === "script") {
      setTestError("Script APIs execution is not supported until MVP-5.");
      return;
    }
    let parsedParams: Record<string, unknown> = {};
    try {
      parsedParams = testParams.trim() ? JSON.parse(testParams) : {};
      if (typeof parsedParams !== "object" || Array.isArray(parsedParams)) {
        throw new Error("Params must be an object");
      }
    } catch {
      setTestError("Params should be valid JSON object.");
      return;
    }
    let parsedInput: Record<string, unknown> | null = null;
    if (selectedApi.logic_type === "workflow") {
      try {
        parsedInput = testInput.trim() ? JSON.parse(testInput) : null;
      } catch {
        setTestError("Input should be valid JSON.");
        return;
      }
    }
    const limitValue = Math.min(Math.max(Number(testLimit) || 200, 1), 1000);
    setIsExecuting(true);
    setTestError(null);
    try {
      const bodyPayload: Record<string, unknown> = {
        params: parsedParams,
        limit: limitValue,
        executed_by: executedBy || "ops-builder",
      };
      if (selectedApi.logic_type === "workflow") {
        bodyPayload.input = parsedInput;
      }
      const response = await fetch(buildApiUrl(`/api-manager/apis/${selectedId}/execute`, apiBaseUrl), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyPayload),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Execution failed");
      }
      if (selectedApi.logic_type === "workflow") {
        setWorkflowResult(payload.data.result);
        setExecutionResult(null);
        setStatusMessage("Workflow executed");
      } else {
        setExecutionResult(payload.data.result);
        setShowJsonResult(false);
        setWorkflowResult(null);
        setStatusMessage("Execution succeeded");
      }
      await fetchExecLogs();
    } catch (error) {
      console.error("Execution failed", error);
      setTestError(error instanceof Error ? error.message : "Execution failed");
      setStatusMessage("Execution failed");
      setWorkflowResult(null);
    } finally {
      setIsExecuting(false);
    }
  };

  const applyLogParams = (log: ExecLogEntry) => {
    setTestParams(JSON.stringify(log.request_params ?? {}, null, 2));
    setExecutedBy(log.executed_by ?? "ops-builder");
  };

  const handleDryRunFromEditor = async () => {
    setIsExecuting(true);
    const start = Date.now();
    try {
      // For HTTP, logic_body is already updated by useEffect to be the spec JSON
      const dryPayload = {
        logic_type: logicType,
        logic_body: logicBody,
        params: safeParseJson(paramSchemaText),
        runtime_policy: safeParseJson(runtimePolicyText),
      };

      const response = await fetch(buildApiUrl("/api-manager/dry-run", apiBaseUrl), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dryPayload),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? body.detail ?? "Dry-run failed");
      }
      const duration = Date.now() - start;
      const result = body.data.result;

      setExecutionResult({
        ...result,
        duration_ms: result.duration_ms || duration,
      });
      setShowLogicResult(true);
      setStatusMessage("Dry-run 실행 성공.");
      setWorkflowResult(null);
    } catch (error) {
      console.error("Dry-run failed", error);
      setStatusMessage(error instanceof Error ? error.message : "Dry-run 실패");
      setExecutionResult(null);
    } finally {
      setIsExecuting(false);
    }
  };

  const testResultsArea = (
    <div className="space-y-4">
      <p className="text-xs uppercase tracking-normal text-slate-500">Execution result</p>
      {selectedApi?.logic_type === "workflow" ? (
        workflowResult ? (
          <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200">
            <div className="space-y-2">
              {workflowResult.steps.map((step) => (
                <div
                  key={step.node_id}
                  className="rounded-2xl border border-slate-800 bg-slate-950/30 p-3 text-xs text-slate-100"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">
                      [{step.node_type}] {step.node_id}
                    </span>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-normal ${step.status === "success"
                        ? "border-emerald-400 text-emerald-300"
                        : "border-rose-500 text-rose-300"
                        }`}
                    >
                      {step.status}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-400">
                    Duration {step.duration_ms} ms · Rows {step.row_count}
                  </p>
                  {step.error_message ? (
                    <p className="text-[10px] text-rose-400">Error: {step.error_message}</p>
                  ) : null}
                </div>
              ))}
            </div>
            <div>
              <p className="text-xs uppercase tracking-normal text-slate-500">Final output</p>
              <pre className="mt-2 max-h-60 overflow-auto rounded-xl bg-slate-950/70 p-3 text-xs text-slate-100 custom-scrollbar">
                {JSON.stringify(workflowResult.final_output, null, 2)}
              </pre>
              <p className="mt-2 text-[10px] uppercase tracking-normal text-slate-400">
                References: {workflowResult.references.length}
              </p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Execute the workflow to see results here.</p>
        )
      ) : executionResult ? (
        <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200">
          <div className="flex items-center justify-between">
            <div>
              <p>Rows: {executionResult.row_count}</p>
              <p>Duration: {executionResult.duration_ms} ms</p>
            </div>
            <button
              onClick={() => setShowJsonResult((prev) => !prev)}
              className="text-[10px] uppercase tracking-normal text-slate-400 underline"
            >
              {showJsonResult ? "Hide JSON" : "Show JSON"}
            </button>
          </div>
          {showJsonResult ? (
            <pre className="max-h-60 overflow-auto rounded-xl bg-slate-950/70 p-3 text-xs text-slate-100 custom-scrollbar">
              {JSON.stringify(executionResult, null, 2)}
            </pre>
          ) : executionResult.columns.length === 0 ? (
            <p className="text-xs text-slate-400">No columns returned.</p>
          ) : (
            <div className="overflow-auto custom-scrollbar">
              <table className="min-w-full text-left text-xs text-slate-200">
                <thead>
                  <tr>
                    {executionResult.columns.map((column) => (
                      <th
                        key={column}
                        className="border-b border-slate-800 px-2 py-1 uppercase tracking-normal text-slate-500"
                      >
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {executionResult.rows.map((row, rowIndex) => (
                    <tr
                      key={`row-${rowIndex}`}
                      className={rowIndex % 2 === 0 ? "bg-slate-950/40" : "bg-slate-900/40"}
                    >
                      {executionResult.columns.map((column) => (
                        <td key={`${rowIndex}-${column}`} className="px-2 py-1 align-top">
                          <pre className="m-0 text-[12px] text-slate-100">{String(row[column] ?? "")}</pre>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-500">Execute the SQL to see results here.</p>
      )}
      <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="flex items-center justify-between">
          <p className="text-xs uppercase tracking-normal text-slate-500">Execution logs</p>
          <span className="text-[10px] uppercase tracking-normal text-slate-400">
            {execLogs.length} entries
          </span>
        </div>
        {logsLoading ? (
          <p className="text-xs text-slate-400">Loading logs…</p>
        ) : execLogs.length === 0 ? (
          <p className="text-xs text-slate-400">No executions yet.</p>
        ) : (
          <div className="space-y-2">
            {execLogs.map((log) => (
              <button
                key={log.exec_id}
                onClick={() => applyLogParams(log)}
                className="w-full rounded-2xl border border-slate-800 bg-slate-950/30 p-3 text-left text-xs text-slate-200 transition hover:border-slate-500"
              >
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span>
                    {log.status.toUpperCase()} · {new Date(log.executed_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}
                  </span>
                  <span>
                    {log.row_count} rows · {log.duration_ms} ms
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-slate-300">by {log.executed_by ?? "ops-builder"}</p>
                {log.request_params ? (
                  <pre className="mt-2 max-h-20 overflow-auto text-[10px] text-slate-400 custom-scrollbar">
                    {JSON.stringify(log.request_params, null, 2)}
                  </pre>
                ) : null}
                {log.error_message ? (
                  <p className="mt-1 text-[10px] text-rose-400">Error: {log.error_message}</p>
                ) : null}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const definitionLogicContent = (
    <div className="space-y-4">
      {activeTab === "definition" && (
        <div className="space-y-3">
          <label className="text-xs uppercase tracking-normal text-slate-500">
            API Name
            <input
              value={definitionDraft.api_name}
              onChange={(event) =>
                setDefinitionDraft((prev) => ({ ...prev, api_name: event.target.value }))
              }
              className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
              disabled={isSystemScope}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-xs uppercase tracking-normal text-slate-500">
              Method
              <select
                value={definitionDraft.method}
                onChange={(event) =>
                  setDefinitionDraft((prev) => ({ ...prev, method: event.target.value as ApiDraft["method"] }))
                }
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
                disabled={isSystemScope}
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
              </select>
            </label>
            <label className="text-xs uppercase tracking-normal text-slate-500">
              Endpoint
              <input
                value={definitionDraft.endpoint}
                onChange={(event) =>
                  setDefinitionDraft((prev) => ({ ...prev, endpoint: event.target.value }))
                }
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
                disabled={isSystemScope}
              />
            </label>
          </div>
          <label className="text-xs uppercase tracking-normal text-slate-500">
            Description
            <textarea
              value={definitionDraft.description ?? ""}
              onChange={(event) =>
                setDefinitionDraft((prev) => ({ ...prev, description: event.target.value }))
              }
              className="mt-2 h-24 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500 custom-scrollbar"
              disabled={isSystemScope}
            />
          </label>
          {selectedDiscovered ? (
            <div className="space-y-2 rounded-2xl border border-slate-800 bg-slate-900/40 p-3 text-[11px] text-slate-200">
              <p className="text-[10px] uppercase tracking-normal text-slate-500">Supported actions / constraints</p>
              {selectedDiscovered.summary ? (
                <p className="text-sm text-slate-200">{selectedDiscovered.summary}</p>
              ) : null}
              {discoveredConstraintLines.map((line, index) => (
                <p key={index} className="text-[11px] text-slate-400">
                  {line}
                </p>
              ))}
              <button
                onClick={() => handleImportDiscoveredEndpoint(selectedDiscovered)}
                className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-slate-500"
              >
                Import to Custom
              </button>
            </div>
          ) : null}
          <label className="text-xs uppercase tracking-normal text-slate-500">
            Tags (comma separated)
            <input
              value={definitionDraft.tags}
              onChange={(event) => setDefinitionDraft((prev) => ({ ...prev, tags: event.target.value }))}
              className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
              disabled={isSystemScope}
            />
          </label>
          <div className="grid gap-3 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <label className="text-xs uppercase tracking-normal text-slate-500">
              Param Schema (JSON)
              <textarea
                value={paramSchemaText}
                onChange={(event) => setParamSchemaText(event.target.value)}
                className="mt-2 h-[11rem] w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500 custom-scrollbar"
                disabled={isSystemScope && systemView !== "registered"}
              />
            </label>
            <div className="flex flex-col">
              <span className="text-xs uppercase tracking-normal text-slate-500">Runtime Policy (JSON)</span>
              <div className="mt-2 h-[11rem]">
                {!isSystemScope || systemView === "registered" ? (
                  <textarea
                    value={runtimePolicyText}
                    onChange={(event) => setRuntimePolicyText(event.target.value)}
                    className="h-full w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500 custom-scrollbar"
                    disabled={isSystemScope && systemView !== "registered"}
                  />
                ) : (
                  <div className="flex h-full flex-col justify-center rounded-2xl border border-slate-800 bg-slate-900/40 p-3 text-[11px] text-slate-400">
                    Runtime Policy editing is available only for System {'>'} Registered or Custom APIs.
                  </div>
                )}
              </div>
            </div>
          </div>
          <label className="text-xs uppercase tracking-normal text-slate-500 flex items-center gap-2">
            <input
              type="checkbox"
              checked={definitionDraft.is_active}
              onChange={(event) =>
                setDefinitionDraft((prev) => ({ ...prev, is_active: event.target.checked }))
              }
              className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-sky-400 focus:ring-sky-400"
              disabled={isSystemScope}
            />
            Active
          </label>
          <label className="text-xs uppercase tracking-normal text-slate-500">
            Created by
            <input
              value={definitionDraft.created_by}
              onChange={(event) =>
                setDefinitionDraft((prev) => ({ ...prev, created_by: event.target.value }))
              }
              className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
              placeholder="ops-builder"
              disabled={isSystemScope}
            />
          </label>
        </div>
      )}
      {activeTab === "logic" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-normal text-slate-500">
              Logic ({logicTypeLabels[logicType]})
            </p>
            {!isSystemScope ? (
              <div className="flex flex-wrap gap-2">
                {(["sql", "workflow", "python", "script", "http"] as LogicType[]).map((type) => (
                  <button
                    key={type}
                    onClick={() => setLogicType(type)}
                    disabled={!!selectedId}
                    className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-normal transition ${logicType === type
                      ? "border-sky-500 bg-sky-500/10 text-white"
                      : "border-slate-800 bg-slate-950 text-slate-400"
                      } ${!!selectedId ? "opacity-40 cursor-not-allowed" : "hover:border-slate-600 shadow-sm"}`}
                  >
                    {logicTypeLabels[type]}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          {logicType === "script" && !isSystemScope ? (
            <label className="text-xs uppercase tracking-normal text-slate-500 flex flex-col gap-2">
              Script language
              <select
                value={scriptLanguage}
                onChange={(event) =>
                  setScriptLanguage(event.target.value as "python" | "javascript")
                }
                className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
              >
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
              </select>
            </label>
          ) : null}
          <div
            className={`builder-json-shell rounded-2xl border border-slate-800 bg-slate-950/60 transition-all ${
              logicType === "http" ? "h-auto max-h-[500px] overflow-y-auto" : "h-64 overflow-hidden"
            }`}
          >
            {logicType === "http" ? (
              <div className="space-y-4 p-4 text-sm">
                {isSystemScope ? (
                  <p className="text-[11px] text-slate-400">
                    HTTP spec is read-only for system APIs.
                  </p>
                ) : null}
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <label className="flex flex-col gap-1.5 text-xs uppercase tracking-normal text-slate-500">
                    Method
                    <select
                      value={httpSpec.method}
                      onChange={(e) => setHttpSpec((prev) => ({ ...prev, method: e.target.value }))}
                      disabled={isSystemScope}
                      className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <option>GET</option>
                      <option>POST</option>
                      <option>PUT</option>
                      <option>DELETE</option>
                    </select>
                  </label>
                  <label className="flex flex-col gap-1.5 text-xs uppercase tracking-normal text-slate-500">
                    URL
                    <input
                      value={httpSpec.url}
                      onChange={(e) => setHttpSpec((prev) => ({ ...prev, url: e.target.value }))}
                      disabled={isSystemScope}
                      className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
                      placeholder="https://api.example.com/data"
                    />
                  </label>
                </div>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <label className="flex flex-col gap-1.5 text-xs uppercase tracking-normal text-slate-500">
                    Headers (JSON)
                    <textarea
                      value={httpSpec.headers}
                      onChange={(e) => setHttpSpec((prev) => ({ ...prev, headers: e.target.value }))}
                      disabled={isSystemScope}
                      className="h-28 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-white outline-none focus:border-sky-500 custom-scrollbar disabled:cursor-not-allowed disabled:opacity-60"
                    />
                  </label>
                  <label className="flex flex-col gap-1.5 text-xs uppercase tracking-normal text-slate-500">
                    Params (JSON)
                    <textarea
                      value={httpSpec.params}
                      onChange={(e) => setHttpSpec((prev) => ({ ...prev, params: e.target.value }))}
                      disabled={isSystemScope}
                      className="h-28 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-white outline-none focus:border-sky-500 custom-scrollbar disabled:cursor-not-allowed disabled:opacity-60"
                    />
                  </label>
                </div>
                <label className="flex flex-col gap-1.5 text-xs uppercase tracking-normal text-slate-500 pb-2">
                  Body (JSON)
                  <textarea
                    value={httpSpec.body}
                    onChange={(e) => setHttpSpec((prev) => ({ ...prev, body: e.target.value }))}
                    disabled={isSystemScope}
                    className="h-32 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-white outline-none focus:border-sky-500 custom-scrollbar disabled:cursor-not-allowed disabled:opacity-60"
                  />
                </label>
              </div>
            ) : (
              <Editor
                height="100%"
                language={getEditorLanguage(logicType, scriptLanguage)}
                value={logicBody}
                onChange={(value) => setLogicBody(value ?? "")}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  readOnly: isSystemScope,
                }}
              />
            )}
          </div>
        </div>
      )}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-slate-800/60">
        <span className={`text-[11px] uppercase tracking-[0.1em] px-3 py-1 rounded-full border ${statusMessage?.toLowerCase().includes("failed") || statusMessage?.toLowerCase().includes("error")
          ? "text-rose-400 border-rose-500/30 bg-rose-500/5 font-semibold"
          : statusMessage && statusMessage.includes("Saved")
            ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/5"
            : "text-slate-500 border-transparent bg-transparent"
          }`}>
          {statusMessage ?? "정의/로직 저장 대기"}
        </span>
        <div className="flex items-center gap-3">
          {activeTab === "logic" && (logicType === "sql" || logicType === "http" || logicType === "script" || logicType === "python") && (
            <button
              onClick={handleDryRunFromEditor}
              className="rounded-full border border-sky-500/30 bg-sky-500/80 px-5 py-2 text-[12px] font-bold uppercase tracking-wider text-white transition hover:bg-sky-400 hover:shadow-[0_0_15px_rgba(14,165,233,0.3)] disabled:bg-slate-800 disabled:text-slate-500"
              disabled={isExecuting}
            >
              {isExecuting ? "Running…" : `Test ${logicTypeLabels[logicType]} (Dry-run)`}
            </button>
          )}
          <button
            onClick={handleSave}
            className="rounded-full border border-emerald-500/30 bg-emerald-500/80 px-6 py-2 text-[12px] font-bold uppercase tracking-wider text-white transition hover:bg-emerald-400 hover:shadow-[0_0_15px_rgba(16,185,129,0.3)] disabled:bg-slate-800 disabled:text-slate-500"
            disabled={isSaving || isSystemScope}
          >
            {isSaving ? "Saving…" : selectedApi ? "Update API" : "Create API"}
          </button>
        </div>
      </div>
      {showLogicResult && activeTab === "logic" && (
        <div className="mt-4 border-t border-slate-800 pt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-normal text-slate-500">Query Result</span>
            <button
              onClick={() => setShowLogicResult(false)}
              className="text-[10px] text-slate-500 hover:text-slate-300"
            >
              Close
            </button>
          </div>
          {executionResult ? (
            <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <p>Rows: {executionResult.row_count}</p>
                  <p>Duration: {executionResult.duration_ms} ms</p>
                </div>
                <button
                  onClick={() => setShowJsonResult((prev) => !prev)}
                  className="text-[10px] uppercase tracking-normal text-slate-400 underline"
                >
                  {showJsonResult ? "Hide JSON" : "Show JSON"}
                </button>
              </div>
              {showJsonResult ? (
                <pre className="max-h-60 overflow-auto rounded-xl bg-slate-950/70 p-3 text-xs text-slate-100 custom-scrollbar">
                  {JSON.stringify(executionResult, null, 2)}
                </pre>
              ) : executionResult.columns.length === 0 ? (
                <p className="text-xs text-slate-400">No columns returned.</p>
              ) : (
                <div className="overflow-auto custom-scrollbar">
                  <table className="min-w-full text-left text-xs text-slate-200">
                    <thead>
                      <tr>
                        {executionResult.columns.map((column) => (
                          <th
                            key={column}
                            className="border-b border-slate-800 px-2 py-1 uppercase tracking-normal text-slate-500"
                          >
                            {column}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {executionResult.rows.map((row, rowIndex) => (
                        <tr
                          key={`row-${rowIndex}`}
                          className={rowIndex % 2 === 0 ? "bg-slate-950/40" : "bg-slate-900/40"}
                        >
                          {executionResult.columns.map((column) => (
                            <td key={`${rowIndex}-${column}`} className="px-2 py-1 align-top">
                              <pre className="m-0 text-[12px] text-slate-100">{String(row[column] ?? "")}</pre>
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No result available.</p>
          )}
        </div>
      )}
    </div>
  );

  const isSqlApi = selectedApi?.logic_type === "sql";
  const isWorkflowApi = selectedApi?.logic_type === "workflow";
  const isHttpApi = selectedApi?.logic_type === "http";

  const testTabContent = (
    <div className="space-y-3">
      {selectedApi ? (
        <p className="text-[11px] text-slate-400">
          Runtime URL:{" "}
          <span className="font-mono text-[10px] text-slate-200">
            {`${apiBaseUrl}${selectedApi.endpoint}`}
          </span>
        </p>
      ) : null}
      <label className="text-xs uppercase tracking-normal text-slate-500">
        Params JSON
        <textarea
          value={testParams}
          onChange={(event) => setTestParams(event.target.value)}
          className="mt-2 h-32 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500 custom-scrollbar"
        />
      </label>
      {isWorkflowApi ? (
        <label className="text-xs uppercase tracking-normal text-slate-500">
          Input JSON (optional)
          <textarea
            value={testInput}
            onChange={(event) => setTestInput(event.target.value)}
            className="mt-2 h-24 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500 custom-scrollbar"
          />
        </label>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="text-xs uppercase tracking-normal text-slate-500">
          Limit
          <input
            type="number"
            min={1}
            max={1000}
            value={testLimit}
            onChange={(event) => setTestLimit(event.target.value)}
            className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
          />
        </label>
        <label className="text-xs uppercase tracking-normal text-slate-500">
          Executed by
          <input
            value={executedBy}
            onChange={(event) => setExecutedBy(event.target.value)}
            className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
            placeholder="ops-builder"
          />
        </label>
        <div className="flex items-end">
          <button
            onClick={handleExecute}
            className="w-full rounded-2xl border border-slate-800 bg-sky-500/90 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:bg-sky-400 disabled:bg-slate-700"
            disabled={
              !selectedId || isExecuting || (!isSqlApi && !isWorkflowApi && !isHttpApi)
            }
          >
            {isExecuting
              ? "Executing…"
              : isWorkflowApi
                ? "Execute Workflow"
                : "Execute API"}
          </button>
        </div>
      </div>
      {selectedApi && selectedApi.logic_type === "script" ? (
        <p className="text-xs text-slate-400">
          Script APIs are saved for future execution support in MVP-5.
        </p>
      ) : null}
      {testError ? <p className="text-xs text-rose-400">{testError}</p> : null}
    </div>
  );

  const centerTop = (
    <div className="space-y-4">
      <div className="flex gap-3">
        {tabOptions.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-normal ${activeTab === tab.id
              ? "border-sky-500 bg-sky-500/10 text-white"
              : "border-slate-800 bg-slate-950 text-slate-400"
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {activeTab === "test" ? testTabContent : definitionLogicContent}
    </div>
  );

  const centerBottom = (
    <div className="space-y-4">
      {activeTab === "test" ? (
        testResultsArea
      ) : (
        <>
          <p className="text-xs uppercase tracking-normal text-slate-500">Metadata (Current Editor)</p>
          <div className="space-y-2 rounded-2xl border border-slate-800 bg-slate-900/40 p-3 text-sm text-slate-300">
            <p>
              Endpoint: <span className="text-slate-100">{definitionDraft.endpoint || "(new)"}</span>
            </p>
            <p>
              Logic type: <span className="text-sky-400 font-mono">{logicTypeLabels[logicType]}</span>
            </p>
            {selectedApi && (
              <p className="border-t border-slate-800/60 pt-2 text-[10px] text-slate-500">
                Editing: {selectedApi.api_name} ({selectedApi.api_id})
              </p>
            )}
            <p className="text-[11px] text-amber-400/80">{statusMessage}</p>
          </div>
        </>
      )}
    </div>
  );

  const leftPane = (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs uppercase tracking-normal text-slate-500">API 목록</h3>
        <div className="flex gap-2 text-[10px] uppercase tracking-normal">
          {(["custom"] as ScopeType[])
            .concat(enableSystemApis ? (["system"] as ScopeType[]) : [])
            .map((item) => (
              <button
                key={item}
                onClick={() => setScope(item as ScopeType)}
                className={`rounded-full border px-3 py-1 transition ${scope === item
                  ? "border-sky-500 bg-sky-500/10 text-white"
                  : "border-slate-700 bg-slate-950 text-slate-400"
                  }`}
              >
                {SCOPE_LABELS[item]}
              </button>
            ))}
        </div>
      </div>
      {scope === "system" && enableSystemApis ? (
        <>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[10px] uppercase tracking-normal text-slate-500">
              <div className="flex items-center gap-2">
                {(["discovered", "registered"] as SystemView[]).map((view) => (
                  <button
                    key={view}
                    onClick={() => setSystemView(view)}
                    className={`rounded-full border px-2 py-1 text-[10px] uppercase tracking-normal transition ${systemView === view
                      ? "border-sky-500 bg-sky-500/10 text-white"
                      : "border-slate-700 bg-slate-950 text-slate-400"
                      }`}
                  >
                    {view}
                  </button>
                ))}
              </div>
            </div>
            {systemView === "discovered" ? (
              <>
                <p className="text-[11px] text-slate-400">Discovered endpoints are read-only.</p>
                <p className="text-[11px] text-slate-500">
                  Discovered from source (OpenAPI). These are not DB-registered APIs.
                </p>
                <div className="text-[10px] uppercase tracking-normal text-slate-500">
                  Last fetch:{" "}
                  <span className="text-slate-300">
                    {discoveredFetchAt
                      ? new Date(discoveredFetchAt).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })
                      : "-"}
                  </span>{" "}
                  · Status:{" "}
                  <span className={discoveredFetchStatus === "error" ? "text-rose-300" : "text-slate-300"}>
                    {discoveredFetchStatus}
                  </span>
                  {discoveredError ? (
                    <span className="ml-2 text-rose-300">Error: {discoveredError}</span>
                  ) : null}
                </div>
              </>
            ) : (
              <>
                <p className="text-[11px] text-slate-400">Registered APIs are read-only.</p>
                {systemFetchStatus === "error" ? (
                  <div className="rounded-2xl border border-amber-500/60 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200">
                    Server list unavailable. Showing local cache only.
                  </div>
                ) : null}
                <div className="text-[10px] uppercase tracking-normal text-slate-500">
                  Last fetch:{" "}
                  <span className="text-slate-300">
                    {systemFetchAt
                      ? new Date(systemFetchAt).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })
                      : "-"}
                  </span>{" "}
                  · Status:{" "}
                  <span className={systemFetchStatus === "error" ? "text-rose-300" : "text-slate-300"}>
                    {systemFetchStatus}
                  </span>
                  {systemError ? (
                    <span className="ml-2 text-rose-300">Error: {systemError}</span>
                  ) : null}
                </div>
              </>
            )}
          </div>
          {systemView === "discovered" ? (
            <>
              <div className="flex items-center justify-between">
                <input
                  value={discoveredSearchTerm}
                  onChange={(event) => setDiscoveredSearchTerm(event.target.value)}
                  placeholder="검색"
                  className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
                />
                <button
                  onClick={loadDiscoveredEndpoints}
                  className="ml-2 rounded-full border border-slate-700 bg-slate-950 px-3 py-2 text-[10px] uppercase tracking-normal text-slate-400 transition hover:border-slate-500"
                >
                  Refresh
                </button>
              </div>
              {discoveredError ? <p className="text-xs text-rose-400">{discoveredError}</p> : null}
              <div className="max-h-[420px] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/40 custom-scrollbar">
                <table className="min-w-full table-auto text-left text-xs text-slate-200">
                  <thead className="sticky top-0 bg-slate-950/90">
                    <tr>
                      {["method", "path", "summary", "tags", "source"].map((column) => (
                        <th
                          key={column}
                          className="border-b border-slate-800 px-2 py-2 uppercase tracking-normal text-slate-500 whitespace-nowrap"
                        >
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDiscoveredEndpoints.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-3 py-3 text-slate-500">
                          No discovered endpoints found.
                        </td>
                      </tr>
                    ) : (
                      filteredDiscoveredEndpoints.map((endpoint) => (
                        <tr
                          key={`${endpoint.method}-${endpoint.path}`}
                          className={`cursor-pointer border-b border-slate-900/60 ${selectedDiscovered?.path === endpoint.path &&
                            selectedDiscovered?.method === endpoint.method
                            ? "bg-sky-500/10 text-white"
                            : "hover:bg-slate-900/60"
                            }`}
                          onClick={() => {
                            setSelectedDiscovered(endpoint);
                            setSelectedId(null);
                            const draft = buildDraftFromDiscovered(endpoint);
                            applyFinalToForm(draft);
                            setStatusMessage("Discovered endpoint loaded (read-only).");
                                                  setFormBaselineSnapshot(JSON.stringify(draft));
                            setAppliedDraftSnapshot(null);
                            setDraftApi(null);
                            setDraftStatus("idle");
                            setDraftNotes(null);
                          }}
                        >
                          <td className="px-2 py-2 whitespace-nowrap">{endpoint.method}</td>
                          <td className="px-2 py-2 whitespace-nowrap">{endpoint.path}</td>
                          <td className="px-2 py-2 whitespace-nowrap">{endpoint.summary ?? "-"}</td>
                          <td className="px-2 py-2 whitespace-nowrap">{endpoint.tags?.join(", ") || "-"}</td>
                          <td className="px-2 py-2 whitespace-nowrap">
                            <span className="rounded-full border border-slate-700 px-2 py-1 text-[10px] uppercase tracking-normal text-slate-400">
                              {endpoint.source}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              {/* Detail details moved to central pane */}
            </>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <input
                  value={systemSearchTerm}
                  onChange={(event) => setSystemSearchTerm(event.target.value)}
                  placeholder="검색"
                  className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
                />
                <div className="ml-2 flex items-center gap-2">
                  <button
                    onClick={() => loadApis(selectedId ?? undefined)}
                    className="rounded-full border border-slate-700 bg-slate-950 px-3 py-2 text-[10px] uppercase tracking-normal text-slate-400 transition hover:border-slate-500"
                  >
                    Refresh
                  </button>
                </div>
              </div>
              {systemError ? <p className="text-xs text-rose-400">{systemError}</p> : null}
              <div className="max-h-[420px] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/40 custom-scrollbar">
                <table className="min-w-full table-auto text-left text-xs text-slate-200">
                  <thead className="sticky top-0 bg-slate-950/90">
                    <tr>
                      {["method", "endpoint", "api_name", "tags", "updated_at", "source"].map((column) => (
                        <th
                          key={column}
                          className="border-b border-slate-800 px-2 py-2 uppercase tracking-normal text-slate-500 whitespace-nowrap"
                        >
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredSystemApis.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-3 py-3 text-slate-500">
                          No registered APIs found.
                        </td>
                      </tr>
                    ) : (
                      filteredSystemApis.map((api) => (
                        <tr
                          key={api.api_id}
                          className={`cursor-pointer border-b border-slate-900/60 ${selectedApi?.api_id === api.api_id
                            ? "bg-sky-500/10 text-white"
                            : "hover:bg-slate-900/60"
                            }`}
                          onClick={() => {
                            setSelectedId(api.api_id);
                            setDraftApi(null);
                            setDraftStatus("idle");
                            setDraftNotes(null);
                          }}
                        >
                          <td className="px-2 py-2 whitespace-nowrap">{api.method}</td>
                          <td className="px-2 py-2 whitespace-nowrap">{api.endpoint}</td>
                          <td className="px-2 py-2 whitespace-nowrap">{api.api_name}</td>
                          <td className="px-2 py-2 whitespace-nowrap">{api.tags.join(", ") || "-"}</td>
                          <td className="px-2 py-2 whitespace-nowrap">
                            {new Date(api.updated_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}
                          </td>
                          <td className="px-2 py-2 whitespace-nowrap">
                            <span className="rounded-full border border-slate-700 px-2 py-1 text-[10px] uppercase tracking-normal text-slate-400">
                              {api.source}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-normal">
            {[
              { id: "all", label: "All" },
              { id: "sql", label: "SQL" },
              { id: "workflow", label: "Workflow" },
              { id: "python", label: "Python" },
              { id: "script", label: "Script" },
              { id: "http", label: "HTTP" },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setLogicFilter(item.id as "all" | LogicType)}
                className={`rounded-full border px-3 py-1 transition ${logicFilter === item.id
                  ? "border-sky-500 bg-sky-500/10 text-white"
                  : "border-slate-700 bg-slate-950 text-slate-400"
                  }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <input
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="검색"
            className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
          />
          <div className="space-y-2 max-h-[360px] overflow-auto custom-scrollbar">
            {filteredApis.length === 0 ? (
              <p className="text-xs text-slate-500">검색 결과 없음</p>
            ) : (
              filteredApis.map((api) => (
                <button
                  key={api.api_id}
                  onClick={() => setSelectedId(api.api_id)}
                  className={`w-full rounded-2xl border px-3 py-2 text-left text-sm transition flex items-center gap-3 whitespace-nowrap overflow-hidden ${selectedId === api.api_id
                    ? "border-sky-400 bg-sky-500/10 text-white"
                    : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-600"
                    }`}
                >
                  <div className="flex flex-col flex-1 overflow-hidden">
                    <div className="flex items-center gap-2 overflow-hidden">
                      <span className="text-[10px] uppercase text-slate-500 min-w-8">{api.method}</span>
                      <span className="font-semibold truncate">{api.api_name}</span>
                      {((api.source === "local" && api.api_id !== "applied-draft-temp") || api.api_id.startsWith("local-")) && (
                        <span className="rounded-full border border-amber-500/50 bg-amber-500/10 px-1.5 py-0.2 text-[8px] uppercase tracking-normal text-amber-400">
                          Local
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-500 truncate">{api.endpoint}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </>
      )}
      <button
        onClick={handleNew}
        className={`w-full rounded-2xl border px-3 py-2 text-[10px] uppercase tracking-normal transition ${scope === "system"
          ? "border-slate-700 bg-slate-900 text-slate-600 cursor-not-allowed"
          : "border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-600"
          }`}
        disabled={scope === "system"}
      >
        New API
      </button>
    </div>
  );

  const COPILOT_INSTRUCTION =
    "Return ONLY ONE JSON object. No markdown. type=api_draft. \n" +
    "Example (SQL): {\"type\":\"api_draft\",\"draft\":{\"api_name\":\"...\",\"method\":\"GET\",\"endpoint\":\"/api-manager/...\",\"logic\":{\"type\":\"sql\",\"query\":\"SELECT 1\"},\"is_active\":true,\"runtime_policy\":{}}}\n" +
    "Example (HTTP): {\"type\":\"api_draft\",\"draft\":{\"api_name\":\"...\",\"method\":\"GET\",\"endpoint\":\"/api-manager/...\",\"logic\":{\"type\":\"http\",\"spec\":{\"method\":\"GET\",\"url\":\"https://...\"}},\"is_active\":true,\"runtime_policy\":{}}}";

  const processAssistantDraft = useCallback(
    (messageText: string, isComplete: boolean) => {
      setLastAssistantRaw(messageText);
      const baseDraft = draftApi ?? (selectedApi ? apiToDraft(selectedApi) : buildDraftFromForm());
      const result = parseApiDraft(messageText, baseDraft);
      setLastParseStatus(result.ok ? "success" : "fail");
      setLastParseError(result.error ?? null);

      if (result.ok && result.draft) {
        setDraftApi(result.draft);
        setDraftStatus("draft_ready");
        setDraftNotes(result.notes || "AI 드래프트가 준비되었습니다.");
        setDraftErrors([]);
        setDraftWarnings([]);
        setDraftTestOk(null);
        setPreviewJson(JSON.stringify(result.draft, null, 2));
        setPreviewSummary(`${result.draft.method} ${result.draft.endpoint}`);
      } else {
        // While streaming, don't show "failed to extract" as an error immediately
        // Just keep the status as "idle" or a special "typing" status
        if (isComplete) {
          setDraftApi(null);
          setPreviewJson(null);
          setPreviewSummary(null);
          setDraftStatus("error");
          setDraftNotes(result.error ?? "AI 드래프트를 해석할 수 없습니다.");
          setDraftTestOk(false);
        } else if (draftStatus !== "draft_ready") {
          // Keep looking but don't alarm the user
          setDraftStatus("idle");
          setDraftNotes("AI가 답변을 생성 중입니다...");
        }
      }
    },
    [draftApi, selectedApi, buildDraftFromForm, draftStatus]
  );

  const handleAssistantMessage = useCallback(
    (messageText: string) => {
      processAssistantDraft(messageText, false);
    },
    [processAssistantDraft]
  );

  const handleAssistantMessageComplete = useCallback(
    (messageText: string) => {
      processAssistantDraft(messageText, true);
    },
    [processAssistantDraft]
  );

  const showDebug = process.env.NODE_ENV !== "production";

  const rightPane = (
    <div className="space-y-4">
      <BuilderCopilotPanel
        instructionPrompt={COPILOT_INSTRUCTION}
        onAssistantMessage={handleAssistantMessage}
        onAssistantMessageComplete={handleAssistantMessageComplete}
        onUserMessage={() => {
          setDraftApi(null);
          setDraftStatus("idle");
          setDraftNotes(null);
          setDraftErrors([]);
          setDraftWarnings([]);
          setDraftTestOk(null);
          setPreviewJson(null);
          setPreviewSummary(null);
          setDraftDiff(null);
        }}
        inputPlaceholder="API 드래프트를 설명해 주세요..."
      />
      <div className="space-y-3 rounded-3xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-normal text-slate-500">Draft status</span>
          <span className="text-sm font-semibold text-white">
            {draftStatusLabels[draftStatus] ?? draftStatus}
          </span>
        </div>
        {draftNotes ? <p className="text-sm text-slate-300">{draftNotes}</p> : null}
        {draftDiff ? (
          <ul className="space-y-1 text-[11px] text-slate-400">
            {draftDiff.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        ) : null}
        {draftStatus === "outdated" ? (
          <div className="rounded-2xl border border-amber-500/60 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200">
            Draft is outdated. Apply again or regenerate.
          </div>
        ) : null}
        <div className="grid gap-2 sm:grid-cols-2">
          <button
            onClick={handlePreviewDraft}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-sky-500"
          >
            Preview
          </button>
          <button
            onClick={handleTestDraft}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-emerald-400"
          >
            Test (Dry-run)
          </button>
          <button
            onClick={handleApplyDraft}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-indigo-400"
            disabled={!draftApi || draftTestOk !== true}
          >
            Apply
          </button>
          <button
            onClick={handleSaveLocalDraft}
            className="rounded-2xl border border-slate-800 bg-emerald-500/70 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:bg-emerald-400"
            disabled={!draftApi || draftTestOk !== true}
          >
            Save (Local)
          </button>
        </div>
        {!draftApi && (
          <p className="text-xs text-slate-400">
            No draft yet. Ask the copilot to generate one.
            {lastParseError ? ` Parse error: ${lastParseError}` : ""}
          </p>
        )}
        {draftErrors.length > 0 && (
          <div className="space-y-1 rounded-2xl border border-rose-500/60 bg-rose-500/5 px-3 py-2 text-[11px] text-rose-200">
            {draftErrors.map((error) => (
              <p key={error}>{error}</p>
            ))}
          </div>
        )}
        {draftWarnings.length > 0 && (
          <div className="space-y-1 rounded-2xl border border-amber-500/60 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-200">
            {draftWarnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        )}
        {previewSummary && previewJson ? (
          <div className="space-y-2 rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-[11px] text-slate-200">
            <p className="text-xs uppercase tracking-normal text-slate-500">Preview</p>
            <p className="text-sm text-white">{previewSummary}</p>
            <pre className="max-h-48 overflow-auto rounded-xl bg-slate-900/50 p-2 text-[11px] text-slate-300 custom-scrollbar">
              {previewJson}
            </pre>
          </div>
        ) : null}
        {showDebug ? (
          <details className="rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-[11px] text-slate-300">
            <summary className="cursor-pointer text-xs uppercase tracking-normal text-slate-400">
              Debug
            </summary>
            <div className="mt-2 space-y-1">
              <p className="text-[10px] uppercase tracking-normal text-slate-500">
                Save target: {saveTarget ?? "none"}
              </p>
              {lastSaveError ? (
                <p className="text-[11px] text-rose-300">Save error: {lastSaveError}</p>
              ) : null}
              <p className="text-[10px] uppercase tracking-normal text-slate-500">Selected API</p>
              <p className="text-[11px] text-slate-200">
                {selectedApi ? `${selectedApi.api_name} (${selectedApi.api_id})` : "새 API"}
              </p>
              <p className="text-[10px] uppercase tracking-normal text-slate-500">
                Parse status: {lastParseStatus}
              </p>
              {lastParseError ? (
                <p className="text-[11px] text-rose-300">Error: {lastParseError}</p>
              ) : null}
              <p className="text-[10px] uppercase tracking-normal text-slate-500">Last assistant raw</p>
              <pre className="max-h-32 overflow-auto rounded-xl bg-slate-900/60 p-2 text-[10px] text-slate-200">
                {lastAssistantRaw || "없음"}
              </pre>
              {draftApi ? (
                <>
                  <p className="text-[10px] uppercase tracking-normal text-slate-500">Draft JSON</p>
                  <pre className="max-h-32 overflow-auto rounded-xl bg-slate-900/60 p-2 text-[10px] text-slate-200 custom-scrollbar">
                    {JSON.stringify(draftApi, null, 2)}
                  </pre>
                </>
              ) : null}
            </div>
          </details>
        ) : null}
      </div>
    </div>
  );

  return (
    <div className="py-6">
      <h1 className="text-2xl font-semibold text-white">API Manager</h1>
      <p className="mb-6 text-sm text-slate-400">
        Builder shell for defining executable APIs that power OPS and orchestration tools.
      </p>
      <BuilderShell
        leftPane={leftPane}
        centerTop={centerTop}
        centerBottom={centerBottom}
        rightPane={rightPane}
      />
    </div>
  );
}
