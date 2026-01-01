"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import BuilderShell from "../../components/builder/BuilderShell";
import BuilderCopilotPanel from "../../components/chat/BuilderCopilotPanel";
import { saveApiWithFallback } from "../../lib/apiManagerSave";
import Editor from "@monaco-editor/react";

type ScopeType = "system" | "custom";
type CenterTab = "definition" | "logic" | "test";
type LogicType = "sql" | "workflow" | "python" | "script";
type SystemView = "discovered" | "registered";

interface ApiDefinitionItem {
  api_id: string;
  api_name: string;
  api_type: ScopeType;
  method: "GET" | "POST";
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

const DEFAULT_SCOPE: ScopeType = "custom";
const DEFAULT_TAB: CenterTab = "definition";
const SCOPE_LABELS: Record<ScopeType, string> = {
  custom: "custom",
  system: "system",
};

const normalizeBaseUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "http://localhost:8000";

const buildStatusMessage = (selected: ApiDefinitionItem | null) => {
  if (!selected) {
    return "Select an API to view or edit its definition.";
  }
  return `Last updated ${new Date(selected.updated_at).toLocaleString("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })} by ${selected.created_by ?? "unknown"}`;
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
};

const getEditorLanguage = (logicType: LogicType, scriptLanguage: "python" | "javascript") => {
  if (logicType === "sql") {
    return "sql";
  }
  if (logicType === "workflow") {
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

const extractFirstJsonObject = (text: string) => {
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

const applyPatchToDraft = (base: ApiDraft, patchOps: { op: string; path: string; value: unknown }[]) => {
  const draftClone = JSON.parse(JSON.stringify(base)) as ApiDraft;
  for (const op of patchOps ?? []) {
    if (op.op !== "replace") {
      continue;
    }
    const segments = op.path.split("/").filter(Boolean);
    if (segments.length === 0) {
      continue;
    }
    let cursor: any = draftClone;
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
        cursor = cursor[numericIndex];
        continue;
      }
      if (typeof cursor[segment] === "undefined" || cursor[segment] === null) {
        cursor[segment] = {};
      }
      cursor = cursor[segment];
    }
    const lastSegment = segments[segments.length - 1];
    const numericLast = Number.parseInt(lastSegment, 10);
    if (!Number.isNaN(numericLast) && Number.isInteger(numericLast)) {
      if (!Array.isArray(cursor)) {
        cursor = [];
      }
      cursor[numericLast] = op.value;
    } else {
      cursor[lastSegment] = op.value;
    }
  }
  return draftClone;
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
  if (!draft.logic || draft.logic.type !== "sql") {
    return "draft.logic.type은 sql이어야 합니다.";
  }
  if (!draft.logic.query?.trim()) {
    return "draft.logic.query 값이 필요합니다.";
  }
  return null;
};

const normalizeDraftPayload = (payload: unknown, baseDraft: ApiDraft) => {
  if (typeof payload !== "object" || payload === null) {
    return { ok: false, error: "JSON이 객체가 아닙니다." };
  }
  const obj = payload as Record<string, unknown>;
  if (obj.type !== "api_draft") {
    return { ok: false, error: "type=api_draft인 객체가 아닙니다." };
  }
  const mode = obj.mode;
  if (mode === "replace" || typeof mode === "undefined") {
    if (!obj.draft || typeof obj.draft !== "object") {
      return { ok: false, error: "draft 필드가 없습니다." };
    }
    const draft = obj.draft as ApiDraft;
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
    const updated = applyPatchToDraft(baseDraft, obj.patch as any);
    const shapeError = validateDraftShape(updated);
    if (shapeError) {
      return { ok: false, error: shapeError };
    }
    return { ok: true, draft: updated, notes: (obj.notes as string) ?? null };
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

const parseApiDraft = (text: string, baseDraft: ApiDraft) => {
  const rawCandidates = [stripCodeFences(text), text];
  for (const candidate of rawCandidates) {
    if (!candidate.trim()) {
      continue;
    }
    const direct = tryParseJson(candidate);
    if (direct) {
      return normalizeDraftPayload(direct, baseDraft);
    }
    try {
      const extracted = extractFirstJsonObject(candidate);
      const parsed = JSON.parse(extracted);
      return normalizeDraftPayload(parsed, baseDraft);
    } catch {
      // continue to next candidate
    }
  }
  return { ok: false, error: "JSON 객체를 추출할 수 없습니다." };
};

const apiToDraft = (api: ApiDefinitionItem): ApiDraft => ({
  api_name: api.api_name,
  method: api.method,
  endpoint: api.endpoint,
  description: api.description ?? "",
  tags: api.tags ?? [],
  params_schema: api.param_schema ?? {},
  logic: {
    type: "sql",
    query: api.logic_body,
  },
});

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
  if (!draft.endpoint.startsWith("/api-manager/")) {
    errors.push("/api-manager/로 시작하는 엔드포인트만 허용됩니다.");
  }
  if (!["GET", "POST", "PUT", "DELETE"].includes(draft.method)) {
    errors.push("HTTP 메서드는 GET/POST/PUT/DELETE 중 하나여야 합니다.");
  }
  if (draft.logic.type !== "sql") {
    errors.push("logic.type은 sql이어야 합니다.");
  }
  if (!draft.logic.query.trim()) {
    errors.push("SQL 쿼리를 입력해야 합니다.");
  }
  const sqlResult = validateSql(draft.logic.query);
  errors.push(...sqlResult.errors);
  warnings.push(...sqlResult.warnings);
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
  if (draft.tags.join(",") !== baseline.tags.join(",")) {
    differences.push(`Tags: ${baseline.tags.join(", ") || "<empty>"} → ${draft.tags.join(", ") || "<empty>"}`);
  }
  if (draft.logic.query !== baseline.logic.query) {
    differences.push("Logic query updated");
  }
  return differences;
};

interface ApiDraft {
  api_name: string;
  method: "GET" | "POST" | "PUT" | "DELETE";
  endpoint: string;
  description: string;
  tags: string[];
  params_schema: Record<string, unknown>;
  logic: {
    type: "sql";
    query: string;
    timeout_ms?: number;
  };
}

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
  const skipAutoSelectRef = useRef(false);
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
  const [testError, setTestError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [logicFilter, setLogicFilter] = useState<"all" | LogicType>("all");
  const [formDirty, setFormDirty] = useState(false);
  const [formBaselineSnapshot, setFormBaselineSnapshot] = useState<string | null>(null);
  const [appliedDraftSnapshot, setAppliedDraftSnapshot] = useState<string | null>(null);
  const [saveTarget, setSaveTarget] = useState<"server" | "local" | null>(null);
  const [lastSaveError, setLastSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!enableSystemApis && scope === "system") {
      setScope("custom");
    }
  }, [enableSystemApis, scope]);

  const selectedApi = useMemo(() => {
    if (scope === "system" && enableSystemApis) {
      return systemApis.find((api) => api.api_id === selectedId) ?? null;
    }
    return apis.find((api) => api.api_id === selectedId) ?? null;
  }, [apis, systemApis, selectedId, scope, enableSystemApis]);

  const buildDraftFromForm = useCallback((): ApiDraft => {
    return {
      api_name: definitionDraft.api_name,
      method: definitionDraft.method,
      endpoint: definitionDraft.endpoint,
      description: definitionDraft.description,
      tags: parseTags(definitionDraft.tags),
      params_schema: safeParseJson(paramSchemaText),
      logic: {
        type: "sql",
        query: logicBody,
      },
    };
  }, [definitionDraft, logicBody, paramSchemaText]);

  const buildSavePayload = useCallback(() => {
    if (isSystemScope) {
      setStatusMessage("System APIs are read-only. Import to Custom to edit.");
      return null;
    }
    if (scope === "custom" && !logicBody.trim()) {
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
    }
    return {
      api_name: definitionDraft.api_name.trim(),
      api_type: scope,
      method: definitionDraft.method.toUpperCase(),
      endpoint: definitionDraft.endpoint.trim(),
      description: definitionDraft.description.trim() || null,
      tags: parseTags(definitionDraft.tags),
      logic_type: logicType,
      logic_body: logicBody.trim(),
      param_schema: parsedParamSchema,
      runtime_policy: parsedRuntimePolicy,
      logic_spec: logicSpecPayload,
      is_active: definitionDraft.is_active,
      created_by: definitionDraft.created_by || "ops-builder",
    };
  }, [
    isSystemScope,
    selectedApi,
    logicBody,
    paramSchemaText,
    runtimePolicyText,
    logicType,
    scriptLanguage,
    definitionDraft,
  ]);

  const buildFormSnapshot = useCallback(() => {
    return JSON.stringify({
      ...buildDraftFromForm(),
      logic_type: logicType,
      runtime_policy: safeParseJson(runtimePolicyText),
    });
  }, [buildDraftFromForm, logicType, runtimePolicyText]);

  const apiBaseUrl = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

  const saveApiToServer = useCallback(
    async (payload: Record<string, unknown>) => {
      const target = selectedApi
        ? `${apiBaseUrl}/api-manager/apis/${selectedApi.api_id}`
        : `${apiBaseUrl}/api-manager/apis`;
      const method = selectedApi ? "PUT" : "POST";
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
  const draftStorageId = selectedId ?? "new";
  const finalStorageId = selectedId ?? (definitionDraft.endpoint || "new");

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
          const url = new URL(`${apiBaseUrl}/api-manager/apis`);
          const response = await fetch(url.toString());
          if (!response.ok) {
            throw new Error("Failed to load system APIs");
          }
          const payload = await response.json();
          const items: ApiDefinitionItem[] = payload.data?.apis ?? [];
          const normalized = items.map((item) => ({ ...item, source: "server" as const }));
          setSystemApis(normalized);
          setSystemFetchStatus("ok");
          setSelectedId((prev) => {
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
          setSelectedId((prev) => {
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
        const url = new URL(`${apiBaseUrl}/api-manager/apis`);
        if (scope) {
          url.searchParams.set("api_type", scope);
        }
        const response = await fetch(url.toString());
        if (!response.ok) {
          throw new Error("Failed to load API definitions");
        }
        const payload = await response.json();
        const items: ApiDefinitionItem[] = payload.data?.apis ?? [];
        setApis(items);
        if (skipAutoSelectRef.current) {
          skipAutoSelectRef.current = false;
          return;
        }
        setSelectedId((prev) => {
          if (preferredId) {
            return preferredId;
          }
          if (prev && items.some((item) => item.api_id === prev)) {
            return prev;
          }
          return items[0]?.api_id ?? null;
        });
      } catch (error) {
        console.error("Unable to fetch APIs", error);
        setApis([]);
        setSelectedId(null);
      }
    },
    [apiBaseUrl, scope, enableSystemApis, getLocalSystemApis]
  );

  const loadDiscoveredEndpoints = useCallback(async () => {
    if (!isSystemScope) {
      return;
    }
    setDiscoveredError(null);
    setDiscoveredFetchStatus("idle");
    setDiscoveredFetchAt(new Date().toISOString());
    try {
      const response = await fetch(`${apiBaseUrl}/api-manager/system/endpoints`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const detail = (payload as { detail?: string }).detail;
        throw new Error(
          detail
            ? `Failed to load discovered endpoints (${response.status}): ${detail}`
            : `Failed to load discovered endpoints (${response.status})`
        );
      }
      const payload = await response.json();
      setDiscoveredEndpoints(payload.data?.endpoints ?? []);
      setDiscoveredFetchStatus("ok");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load discovered endpoints";
      setDiscoveredError(message);
      setDiscoveredFetchStatus("error");
      setDiscoveredEndpoints([]);
    }
  }, [apiBaseUrl, isSystemScope]);

  const fetchExecLogs = useCallback(async () => {
    if (!selectedId) {
      setExecLogs([]);
      return;
    }
    setLogsLoading(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api-manager/apis/${selectedId}/exec-logs?limit=20`);
      if (!response.ok) {
        throw new Error("Failed to load execution logs");
      }
      const payload = await response.json();
      setExecLogs(payload.data?.logs ?? []);
    } catch (error) {
      console.error("Unable to load logs", error);
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
  }, [draftStorageId]);

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
      setFormDirty(false);
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
  }, [draftApi, selectedApi, buildDraftFromForm]);

  useEffect(() => {
    const currentSnapshot = buildFormSnapshot();
    if (formBaselineSnapshot === null) {
      setFormBaselineSnapshot(currentSnapshot);
      return;
    }
    setFormDirty(currentSnapshot !== formBaselineSnapshot);
    if (draftApi && appliedDraftSnapshot && currentSnapshot !== appliedDraftSnapshot) {
      setDraftStatus("outdated");
      setDraftNotes("폼이 변경되어 드래프트가 오래되었습니다.");
    }
  }, [buildFormSnapshot, formBaselineSnapshot, draftApi, appliedDraftSnapshot]);

  useEffect(() => {
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
      setFormDirty(false);
      setFormBaselineSnapshot(JSON.stringify(buildDraftFromForm()));
      return;
    }
    setDefinitionDraft({
      api_name: selectedApi.api_name,
      method: selectedApi.method,
      endpoint: selectedApi.endpoint,
      description: selectedApi.description ?? "",
      tags: selectedApi.tags.join(", "),
      is_active: selectedApi.is_active,
      created_by: selectedApi.created_by ?? "",
    });
    setLogicBody(selectedApi.logic_body);
    setLogicType(selectedApi.logic_type);
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
    setFormDirty(false);
  }, [selectedApi, fetchExecLogs]);

  const filteredApis = useMemo(() => {
    let result = apis;
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
        api.tags.join(",").toLowerCase().includes(lower)
    );
  }, [apis, searchTerm, logicFilter]);

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
        api.tags.join(",").toLowerCase().includes(lower)
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
    setIsSaving(true);
    setSaveTarget(null);
    setLastSaveError(null);
    try {
      const result = await saveApiToServer(payload);
      if (!result.ok) {
        setLastSaveError(result.error ?? "Failed to save API definition");
        setStatusMessage(result.error ?? "Save failed. 확인 로그를 참고하세요.");
        return;
      }
      const saved = result.data as ApiDefinitionItem | null;
      setStatusMessage(selectedApi ? "API updated" : "API created");
      setSaveTarget("server");
      if (saved?.api_id) {
        setSelectedId(saved.api_id);
        await loadApis(saved.api_id);
      } else {
        await loadApis(selectedId ?? undefined);
      }
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

  const handleTestDraft = () => {
    if (!draftApi) {
      setDraftErrors(["AI 드래프트가 없습니다."]);
      return;
    }
    setDraftStatus("testing");
    const validation = validateApiDraft(draftApi);
    setDraftErrors(validation.errors);
    setDraftWarnings(validation.warnings);
    setDraftNotes(validation.ok ? "테스트 통과" : "테스트 실패");
    setDraftTestOk(validation.ok);
    setDraftStatus(validation.ok ? "draft_ready" : "error");
  };

  const applyFinalToForm = (draft: ApiDraft) => {
    setDefinitionDraft((prev) => ({
      ...prev,
      api_name: draft.api_name,
      method: draft.method,
      endpoint: draft.endpoint,
      description: draft.description,
      tags: draft.tags.join(", "),
    }));
    setLogicType("sql");
    setLogicBody(draft.logic.query);
    setParamSchemaText(JSON.stringify(draft.params_schema ?? {}, null, 2));
  };

  const applyDraftToForm = (draft: ApiDraft) => {
    applyFinalToForm(draft);
    setDraftStatus("applied");
    setDraftNotes("드래프트가 폼에 적용되었습니다. 저장 전입니다.");
    setStatusMessage("Draft applied to editor (not saved).");
    setFormDirty(true);
    setAppliedDraftSnapshot(JSON.stringify(draft));
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
    const finalPayload = buildDraftFromForm();
    const storageKey = `${FINAL_STORAGE_PREFIX}${finalStorageId}`;
    setIsSaving(true);
    setSaveTarget(null);
    setLastSaveError(null);
    saveApiWithFallback({
      payload: finalPayload,
      saveApiToServer,
      storage: window.localStorage,
      storageKey,
    })
      .then(async (result) => {
        setSaveTarget(result.target);
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
        }
        setDraftApi(null);
        setDraftStatus("saved");
        setDraftTestOk(null);
        setFormDirty(false);
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

  const handleNew = () => {
    setSelectedId(null);
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
    setScriptLanguage("python");
    setParamSchemaText("{}");
    setRuntimePolicyText("{}");
    setStatusMessage("새 API 정의를 작성하세요.");
    setFormDirty(false);
    setFormBaselineSnapshot(JSON.stringify(buildDraftFromForm()));
    setAppliedDraftSnapshot(null);
  };

  const handleImportSystemApi = useCallback(() => {
    if (!selectedApi) {
      return;
    }
    const imported = apiToDraft(selectedApi);
    skipAutoSelectRef.current = true;
    setScope("custom");
    setSelectedId(null);
    applyFinalToForm(imported);
    setDefinitionDraft((prev) => ({
      ...prev,
      created_by: "imported",
    }));
    setStatusMessage("System API imported into Custom (unsaved).");
    setFormDirty(true);
    setFormBaselineSnapshot(JSON.stringify(imported));
    setAppliedDraftSnapshot(null);
    setDraftApi(null);
    setDraftStatus("idle");
    setDraftNotes(null);
  }, [selectedApi]);

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
    setFormDirty(true);
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
    } catch (error) {
      setTestError("Params should be valid JSON object.");
      return;
    }
    let parsedInput: Record<string, unknown> | null = null;
    if (selectedApi.logic_type === "workflow") {
      try {
        parsedInput = testInput.trim() ? JSON.parse(testInput) : null;
      } catch (error) {
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
      const response = await fetch(`${apiBaseUrl}/api-manager/apis/${selectedId}/execute`, {
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
                  setDefinitionDraft((prev) => ({ ...prev, method: event.target.value as "GET" | "POST" }))
                }
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
                disabled={isSystemScope}
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
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
                value={definitionDraft.description}
                onChange={(event) =>
                  setDefinitionDraft((prev) => ({ ...prev, description: event.target.value }))
                }
                className="mt-2 h-24 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
                disabled={isSystemScope}
              />
          </label>
          <label className="text-xs uppercase tracking-normal text-slate-500">
            Tags (comma separated)
            <input
              value={definitionDraft.tags}
              onChange={(event) => setDefinitionDraft((prev) => ({ ...prev, tags: event.target.value }))}
              className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
              disabled={isSystemScope}
            />
          </label>
          <label className="text-xs uppercase tracking-normal text-slate-500">
            Param Schema (JSON)
            <textarea
              value={paramSchemaText}
              onChange={(event) => setParamSchemaText(event.target.value)}
              className="mt-2 h-64 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
              disabled={isSystemScope}
            />
          </label>
          <label className="text-xs uppercase tracking-normal text-slate-500">
            Runtime Policy (JSON)
            <textarea
              value={runtimePolicyText}
              onChange={(event) => setRuntimePolicyText(event.target.value)}
              className="mt-2 h-24 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
              disabled={isSystemScope}
            />
          </label>
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
                {(["sql", "workflow", "python", "script"] as LogicType[]).map((type) => (
                  <button
                    key={type}
                    onClick={() => setLogicType(type)}
                    className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-normal ${
                      logicType === type
                        ? "border-sky-500 bg-sky-500/10 text-white"
                        : "border-slate-800 bg-slate-950 text-slate-400"
                    }`}
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
          <div className="h-64 rounded-2xl border border-slate-800 bg-slate-950/60">
            <Editor
              height="100%"
              defaultLanguage={getEditorLanguage(logicType, scriptLanguage)}
              value={logicBody}
              onChange={(value) => setLogicBody(value ?? "")}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                readOnly: isSystemScope,
              }}
            />
          </div>
        </div>
      )}
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-normal text-slate-500">
          {statusMessage ?? "정의/로직 저장"}
        </span>
        <button
          onClick={handleSave}
          className="rounded-2xl border border-slate-800 bg-emerald-500/80 px-4 py-2 text-[12px] font-semibold uppercase tracking-normal text-white transition hover:bg-emerald-400 disabled:bg-slate-700"
          disabled={isSaving || isSystemScope}
        >
          {isSaving ? "Saving…" : selectedApi ? "Update API" : "Create API"}
        </button>
      </div>
    </div>
  );

  const isSqlApi = selectedApi?.logic_type === "sql";
  const isWorkflowApi = selectedApi?.logic_type === "workflow";

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
          className="mt-2 h-32 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
        />
      </label>
      {isWorkflowApi ? (
        <label className="text-xs uppercase tracking-normal text-slate-500">
          Input JSON (optional)
          <textarea
            value={testInput}
            onChange={(event) => setTestInput(event.target.value)}
            className="mt-2 h-24 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
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
              !selectedId || isExecuting || (!isSqlApi && !isWorkflowApi)
            }
          >
            {isExecuting
              ? "Executing…"
              : isWorkflowApi
              ? "Execute Workflow"
              : "Execute SQL"}
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
                      className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-normal ${
                        step.status === "success"
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
              <pre className="mt-2 max-h-60 overflow-auto rounded-xl bg-slate-950/70 p-3 text-xs text-slate-100">
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
            <pre className="max-h-60 overflow-auto rounded-xl bg-slate-950/70 p-3 text-xs text-slate-100">
              {JSON.stringify(executionResult, null, 2)}
            </pre>
          ) : executionResult.columns.length === 0 ? (
            <p className="text-xs text-slate-400">No columns returned.</p>
          ) : (
            <div className="overflow-x-auto">
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
                  <pre className="mt-2 max-h-20 overflow-auto text-[10px] text-slate-400">
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

  const centerTop = (
    <div className="space-y-4">
      <div className="flex gap-3">
        {tabOptions.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-normal ${
              activeTab === tab.id
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
          <p className="text-xs uppercase tracking-normal text-slate-500">Metadata</p>
          {selectedApi ? (
            <div className="max-h-20 overflow-auto space-y-2 rounded-2xl border border-slate-800 bg-slate-900/40 p-3 text-sm text-slate-300">
              <p>
                Endpoint: <span className="text-slate-100">{selectedApi.endpoint}</span>
              </p>
              <p>
                Logic type: <span className="text-slate-100">{selectedApi.logic_type}</span>
              </p>
              <p>{statusMessage}</p>
            </div>
          ) : (
            <p className="text-sm text-slate-500">새 API 정의를 만들거나 목록에서 선택하세요.</p>
          )}
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
                className={`rounded-full border px-3 py-1 transition ${
                  scope === item
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
              <span>System (Discovered / Registered)</span>
              <div className="flex items-center gap-2">
                {(["discovered", "registered"] as SystemView[]).map((view) => (
                  <button
                    key={view}
                    onClick={() => setSystemView(view)}
                    className={`rounded-full border px-2 py-1 text-[10px] uppercase tracking-normal transition ${
                      systemView === view
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
                <p className="text-[11px] text-slate-500">
                  Registered APIs (from DB). Code-defined endpoints are not listed here.
                </p>
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
              <div className="max-h-[420px] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950/40">
                <table className="min-w-full text-left text-xs text-slate-200">
                  <thead className="sticky top-0 bg-slate-950/90">
                    <tr>
                      {["method", "path", "summary", "tags", "source"].map((column) => (
                        <th
                          key={column}
                          className="border-b border-slate-800 px-2 py-2 uppercase tracking-normal text-slate-500"
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
                          className={`cursor-pointer border-b border-slate-900/60 ${
                            selectedDiscovered?.path === endpoint.path &&
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
                            setFormDirty(false);
                            setFormBaselineSnapshot(JSON.stringify(draft));
                            setAppliedDraftSnapshot(null);
                            setDraftApi(null);
                            setDraftStatus("idle");
                            setDraftNotes(null);
                          }}
                        >
                          <td className="px-2 py-2">{endpoint.method}</td>
                          <td className="px-2 py-2">{endpoint.path}</td>
                          <td className="px-2 py-2">{endpoint.summary ?? "-"}</td>
                          <td className="px-2 py-2">{endpoint.tags?.join(", ") || "-"}</td>
                          <td className="px-2 py-2">
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
              {selectedDiscovered ? (
                <div className="space-y-2 rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-[11px] text-slate-200">
                  <div className="flex items-center justify-between">
                    <p className="text-xs uppercase tracking-normal text-slate-500">Details</p>
                    <button
                      onClick={() => handleImportDiscoveredEndpoint(selectedDiscovered)}
                      className="rounded-full border border-slate-700 bg-slate-950 px-2 py-1 text-[10px] uppercase tracking-normal text-slate-300 transition hover:border-slate-500"
                    >
                      Import to Custom
                    </button>
                  </div>
                  <p className="text-sm text-white">
                    {selectedDiscovered.method} {selectedDiscovered.path}
                  </p>
                  {selectedDiscovered.description ? (
                    <p className="text-[11px] text-slate-400">{selectedDiscovered.description}</p>
                  ) : null}
                  <pre className="max-h-32 overflow-auto rounded-xl bg-slate-900/60 p-2 text-[10px] text-slate-200">
                    {JSON.stringify(
                      {
                        parameters: selectedDiscovered.parameters ?? [],
                        requestBody: selectedDiscovered.requestBody ?? null,
                        responses: selectedDiscovered.responses ?? null,
                      },
                      null,
                      2
                    )}
                  </pre>
                </div>
              ) : null}
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
                    onClick={handleImportSystemApi}
                    className="rounded-full border border-slate-700 bg-slate-950 px-3 py-2 text-[10px] uppercase tracking-normal text-slate-300 transition hover:border-slate-500 disabled:opacity-60"
                    disabled={!selectedApi}
                  >
                    Import
                  </button>
                  <button
                    onClick={() => loadApis(selectedId ?? undefined)}
                    className="rounded-full border border-slate-700 bg-slate-950 px-3 py-2 text-[10px] uppercase tracking-normal text-slate-400 transition hover:border-slate-500"
                  >
                    Refresh
                  </button>
                </div>
              </div>
              {systemError ? <p className="text-xs text-rose-400">{systemError}</p> : null}
              <div className="max-h-[420px] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950/40">
                <table className="min-w-full text-left text-xs text-slate-200">
                  <thead className="sticky top-0 bg-slate-950/90">
                    <tr>
                      {["method", "endpoint", "api_name", "tags", "updated_at", "source"].map((column) => (
                        <th
                          key={column}
                          className="border-b border-slate-800 px-2 py-2 uppercase tracking-normal text-slate-500"
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
                          className={`cursor-pointer border-b border-slate-900/60 ${
                            selectedApi?.api_id === api.api_id
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
                          <td className="px-2 py-2">{api.method}</td>
                          <td className="px-2 py-2">{api.endpoint}</td>
                          <td className="px-2 py-2">{api.api_name}</td>
                          <td className="px-2 py-2">{api.tags.join(", ") || "-"}</td>
                          <td className="px-2 py-2">
                            {new Date(api.updated_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}
                          </td>
                          <td className="px-2 py-2">
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
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setLogicFilter(item.id as "all" | LogicType)}
                className={`rounded-full border px-3 py-1 transition ${
                  logicFilter === item.id
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
          <div className="space-y-2 max-h-[360px] overflow-y-auto">
            {filteredApis.length === 0 ? (
              <p className="text-xs text-slate-500">검색 결과 없음</p>
            ) : (
              filteredApis.map((api) => (
                <button
                  key={api.api_id}
                  onClick={() => setSelectedId(api.api_id)}
                  className={`w-full rounded-2xl border px-3 py-2 text-left text-sm transition ${
                    selectedApi?.api_id === api.api_id
                      ? "border-sky-400 bg-sky-500/10 text-white"
                      : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-600"
                  }`}
                >
                  <p className="text-[10px] uppercase tracking-normal text-slate-500">{api.method}</p>
                  <p className="font-semibold">{api.api_name}</p>
                  <p className="text-[11px] text-slate-400">{api.endpoint}</p>
                </button>
              ))
            )}
          </div>
        </>
      )}
      <button
        onClick={handleNew}
        className={`w-full rounded-2xl border px-3 py-2 text-[10px] uppercase tracking-normal transition ${
          scope === "system"
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
    "Return ONLY ONE JSON object. No markdown. type=api_draft. Example: {\"type\":\"api_draft\",\"draft\":{\"api_name\":\"...\",\"method\":\"GET\",\"endpoint\":\"/api-manager/...\",\"description\":\"\",\"tags\":[],\"params_schema\":{},\"logic\":{\"type\":\"sql\",\"query\":\"SELECT 1\"}}}";

  const processAssistantDraft = useCallback(
    (messageText: string) => {
      setLastAssistantRaw(messageText);
      const baseDraft = draftApi ?? (selectedApi ? apiToDraft(selectedApi) : buildDraftFromForm());
      const result = parseApiDraft(messageText, baseDraft);
      setLastParseStatus(result.ok ? "success" : "fail");
      setLastParseError(result.error ?? null);
      if (result.ok && result.draft) {
        setDraftApi(result.draft);
        setDraftStatus("draft_ready");
        setDraftNotes((prev) => prev ?? "AI 드래프트가 준비되었습니다.");
        setDraftErrors([]);
        setDraftWarnings([]);
        setDraftTestOk(null);
        setPreviewJson(JSON.stringify(result.draft, null, 2));
        setPreviewSummary(`${result.draft.method} ${result.draft.endpoint}`);
      } else {
        setDraftApi(null);
        setPreviewJson(null);
        setPreviewSummary(null);
        setDraftStatus("error");
        setDraftNotes(result.error ?? "AI 드래프트를 해석할 수 없습니다.");
        setDraftTestOk(false);
      }
    },
    [draftApi, selectedApi, buildDraftFromForm]
  );

  const handleAssistantMessage = useCallback(
    (messageText: string) => {
      processAssistantDraft(messageText);
    },
    [processAssistantDraft]
  );

  const handleAssistantMessageComplete = useCallback(
    (messageText: string) => {
      processAssistantDraft(messageText);
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
            <pre className="max-h-48 overflow-auto rounded-xl bg-slate-900/50 p-2 text-[11px] text-slate-300">
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
                  <pre className="max-h-32 overflow-auto rounded-xl bg-slate-900/60 p-2 text-[10px] text-slate-200">
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
        Builder shell for defining SQL-only APIs that power the next OPS tools.
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
