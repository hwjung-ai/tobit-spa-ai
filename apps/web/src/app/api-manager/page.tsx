"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import BuilderShell from "../../components/builder/BuilderShell";
import { saveApiWithFallback } from "../../lib/apiManagerSave";
import Editor from "@monaco-editor/react";
import {
  FormSection,
  FormFieldGroup,
  ErrorBanner,
  HttpFormBuilder,
  type HttpSpec,
} from "../../components/api-manager";
import SQLQueryBuilder from "../../components/api-manager/SQLQueryBuilder";
import PythonBuilder from "../../components/api-manager/PythonBuilder";
import WorkflowBuilder from "../../components/api-manager/WorkflowBuilder";
import DraftAssistantPanel from "../../components/api-manager/DraftAssistantPanel";
import type {
  ScopeType, CenterTab, LogicType, SystemView,
  ApiDefinitionItem, SystemApiItem, DiscoveredEndpoint, ExecuteResult,
  ExecLogEntry, WorkflowExecuteResult, ApiDraft, HttpLogic, DraftStatus,
} from "../../lib/api-manager/types";
import {
  DEFAULT_SCOPE, DEFAULT_TAB, SCOPE_LABELS, logicTypeLabels,
  DRAFT_STORAGE_PREFIX, FINAL_STORAGE_PREFIX, tabOptions, draftStatusLabels,
  normalizeBaseUrl, buildApiUrl, formatTimestamp, buildStatusMessage,
  parseTags, getEditorLanguage, formatJson, parseJsonObject, safeParseJson,
  normalizeApiDraft, parseApiDraft, apiToDraft, buildTemporaryApiFromDraft,
  validateApiDraft, computeDraftDiff, API_MANAGER_COPILOT_INSTRUCTION,
  API_MANAGER_SCENARIO_FUNCTIONS, validateTemplateBindingsInTexts,
} from "../../lib/api-manager/utils";
import { recordCopilotMetric } from "../../lib/copilot/metrics";

/* Types and utilities imported from lib/api-manager */

type ParsedResponsePayload = {
  data?: Record<string, unknown>;
  message?: string;
  detail?: string;
  [key: string]: unknown;
};

type SaveApiResult =
  | { ok: true; data: Record<string, unknown> | null }
  | { ok: false; error: string; details: unknown };




export default function ApiManagerPage() {
  const normalizeHttpMethod = (method: unknown): HttpSpec["method"] => {
    return method === "POST" || method === "PUT" || method === "DELETE" ? method : "GET";
  };
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
  const [logicHistory, setLogicHistory] = useState<string[]>([""]);
  const [logicHistoryIndex, setLogicHistoryIndex] = useState(0);
  const [logicType, setLogicType] = useState<LogicType>("sql");
  const [scriptLanguage, setScriptLanguage] = useState<"python" | "javascript">("python");
  const [paramSchemaText, setParamSchemaText] = useState("{}");
  const [runtimePolicyText, setRuntimePolicyText] = useState("{}");
  const [httpSpec, setHttpSpec] = useState<HttpSpec>({
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
  const editorUndoRedoRef = useRef<{ trigger: (source: string, id: string, payload: unknown) => void } | null>(null);

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
    setLogicHistory((prev) => {
      const current = prev[logicHistoryIndex];
      if (current === logicBody) {
        return prev;
      }
      const base = prev.slice(0, logicHistoryIndex + 1);
      const next = [...base, logicBody].slice(-100);
      setLogicHistoryIndex(next.length - 1);
      return next;
    });
  }, [logicBody, logicHistoryIndex]);

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
  const parseResponsePayload = useCallback(async (response: Response): Promise<ParsedResponsePayload> => {
    const rawText = await response.text();
    if (!rawText) {
      return {};
    }
    try {
      const parsed = JSON.parse(rawText);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed as ParsedResponsePayload;
      }
      return { data: { value: parsed } };
    } catch {
      return { detail: rawText };
    }
  }, []);

  const saveApiToServer = useCallback(
    async (payload: Record<string, unknown>, forceCreate = false): Promise<SaveApiResult> => {
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
        const result = await parseResponsePayload(response);
        if (!response.ok) {
          return { ok: false, error: result.message ?? "Failed to save API definition", details: result };
        }
        const resultData = (result.data ?? {}) as Record<string, unknown>;
        return { ok: true, data: (resultData.api as Record<string, unknown> | undefined) ?? null };
      } catch (error) {
        return { ok: false, error: error instanceof Error ? error.message : "Network error", details: error };
      }
    },
    [apiBaseUrl, parseResponsePayload, selectedApi]
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
          const payload = await parseResponsePayload(response);
          const payloadData = (payload.data ?? {}) as Record<string, unknown>;
          const items: Record<string, unknown>[] = (payloadData.apis ?? []) as Record<string, unknown>[];
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
            runtime_policy: (item.runtime_policy as Record<string, unknown>) ?? {},
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
        const payload = await parseResponsePayload(response);
        const payloadData = (payload.data ?? {}) as Record<string, unknown>;
        const items: Record<string, unknown>[] = (payloadData.apis ?? []) as Record<string, unknown>[];
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
          runtime_policy: (item.runtime_policy as Record<string, unknown>) ?? {},
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
            if (prev && normalized.some((item) => item.api_id === prev)) {
              return prev;
            }
            return normalized[0]?.api_id ?? null;
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
      const response = await fetch(buildApiUrl("/api-manager/system/endpoints", apiBaseUrl));
      if (!response.ok) {
        throw new Error("Failed to load discovered endpoints");
      }
      const payload = await parseResponsePayload(response);
      const payloadData = (payload.data ?? {}) as Record<string, unknown>;
      const items = (payloadData.endpoints ?? []) as DiscoveredEndpoint[];
      setDiscoveredEndpoints(items);
      setDiscoveredFetchStatus("ok");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load discovered endpoints";
      setDiscoveredError(message);
      setDiscoveredFetchStatus("error");
      setDiscoveredEndpoints([]);
    }
  }, [isSystemScope, apiBaseUrl]);

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
      const payload = await parseResponsePayload(response);
      const payloadData = (payload.data ?? {}) as Record<string, unknown>;
      setExecLogs((payloadData.logs ?? []) as ExecLogEntry[]);
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
          method: normalizeHttpMethod(spec.method),
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
    setLogicHistory([selectedApi.logic_body ?? ""]);
    setLogicHistoryIndex(0);
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
      if ("error" in result) {
        setLastSaveError(result.error ?? "Failed to save API definition");
        setStatusMessage(result.error ?? "Save failed. 확인 로그를 참고하세요.");
        return;
      }
      const saved = result.data as unknown as ApiDefinitionItem | null;
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
      const body = await parseResponsePayload(response);
      if (!response.ok) {
        throw new Error(body.message || body.detail || "Dry-run failed");
      }
      const bodyData = (body.data ?? {}) as Record<string, unknown>;
      setExecutionResult((bodyData.result as ExecuteResult) ?? null);
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
        method: normalizeHttpMethod(spec.method),
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
    setLogicHistory([""]);
    setLogicHistoryIndex(0);
  }, [buildDraftFromForm]);

  const handleLogicUndo = useCallback(() => {
    if (logicHistoryIndex <= 0) {
      editorUndoRedoRef.current?.trigger("toolbar", "undo", null);
      return;
    }
    const nextIndex = logicHistoryIndex - 1;
    const snapshot = logicHistory[nextIndex];
    if (typeof snapshot === "string") {
      setLogicHistoryIndex(nextIndex);
      setLogicBody(snapshot);
      return;
    }
    editorUndoRedoRef.current?.trigger("toolbar", "undo", null);
  }, [logicHistory, logicHistoryIndex]);

  const handleLogicRedo = useCallback(() => {
    if (logicHistoryIndex >= logicHistory.length - 1) {
      editorUndoRedoRef.current?.trigger("toolbar", "redo", null);
      return;
    }
    const nextIndex = logicHistoryIndex + 1;
    const snapshot = logicHistory[nextIndex];
    if (typeof snapshot === "string") {
      setLogicHistoryIndex(nextIndex);
      setLogicBody(snapshot);
      return;
    }
    editorUndoRedoRef.current?.trigger("toolbar", "redo", null);
  }, [logicHistory, logicHistoryIndex]);

  const bindingValidation = useMemo(() => {
    const texts = [logicBody];
    if (logicType === "http") {
      texts.push(httpSpec.url || "");
      texts.push(httpSpec.headers || "");
      texts.push(httpSpec.params || "");
      texts.push(httpSpec.body || "");
    }
    return validateTemplateBindingsInTexts(texts);
  }, [httpSpec.body, httpSpec.headers, httpSpec.params, httpSpec.url, logicBody, logicType]);

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
      const payload = await parseResponsePayload(response);
      if (!response.ok) {
        throw new Error(payload.detail ?? "Execution failed");
      }
      const payloadData = (payload.data ?? {}) as Record<string, unknown>;
      if (selectedApi.logic_type === "workflow") {
        setWorkflowResult((payloadData.result as WorkflowExecuteResult) ?? null);
        setExecutionResult(null);
        setStatusMessage("Workflow executed");
      } else {
        setExecutionResult((payloadData.result as ExecuteResult) ?? null);
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
      if (logicType === "sql") {
        const normalized = logicBody.trim().toUpperCase();
        if (!(normalized.startsWith("SELECT") || normalized.startsWith("WITH"))) {
          throw new Error("SQL dry-run은 SELECT/WITH 조회 쿼리만 지원합니다.");
        }
      }

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
      const body = await parseResponsePayload(response);
      if (!response.ok) {
        throw new Error(body.message ?? body.detail ?? "Dry-run failed");
      }
      const duration = Date.now() - start;
      const bodyData = (body.data ?? {}) as Record<string, unknown>;
      const result = ((bodyData.result as ExecuteResult | null) ?? {}) as ExecuteResult;

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

  const executionColumns = Array.isArray(executionResult?.columns) ? executionResult.columns : [];
  const executionRows = Array.isArray(executionResult?.rows) ? executionResult.rows : [];
  const workflowSteps = Array.isArray(workflowResult?.steps) ? workflowResult.steps : [];
  const workflowReferences = Array.isArray(workflowResult?.references) ? workflowResult.references : [];

  const testResultsArea = (
    <div className="space-y-4">
      <p className="text-xs uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>Execution result</p>
      {selectedApi?.logic_type === "workflow" ? (
        workflowResult ? (
          <div className="space-y-3 rounded-2xl border  dark:  p-4 text-sm " style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground-secondary)" ,  backgroundColor: "var(--surface-overlay)" }}>
            <div className="space-y-2">
              {workflowSteps.map((step) => (
                <div
                  key={step.node_id}
                  className="rounded-2xl border  dark: /30 p-3 text-xs " style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-base)" }}
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
                  <p className="text-[10px] " style={{ color: "var(--muted-foreground)" }}>
                    Duration {step.duration_ms} ms · Rows {step.row_count}
                  </p>
                  {step.error_message ? (
                    <p className="text-[10px] text-rose-400">Error: {step.error_message}</p>
                  ) : null}
                </div>
              ))}
            </div>
            <div>
              <p className="text-xs uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>Final output</p>
              <pre className="mt-2 max-h-60 overflow-auto rounded-xl /70 p-3 text-xs  custom-scrollbar" style={{ color: "var(--foreground)" ,  backgroundColor: "var(--surface-base)" }}>
                {JSON.stringify(workflowResult.final_output, null, 2)}
              </pre>
              <p className="mt-2 text-[10px] uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>
                References: {workflowReferences.length}
              </p>
            </div>
          </div>
        ) : (
          <p className="text-sm " style={{ color: "var(--muted-foreground)" }}>Execute the workflow to see results here.</p>
        )
      ) : executionResult ? (
        <div className="space-y-3 rounded-2xl border  dark:  p-4 text-sm " style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground-secondary)" ,  backgroundColor: "var(--surface-overlay)" }}>
          <div className="flex items-center justify-between">
            <div>
              <p>Rows: {executionResult.row_count}</p>
              <p>Duration: {executionResult.duration_ms} ms</p>
            </div>
            <button
              onClick={() => setShowJsonResult((prev) => !prev)}
              className="text-[10px] uppercase tracking-normal  underline" style={{ color: "var(--muted-foreground)" }}
            >
              {showJsonResult ? "Hide JSON" : "Show JSON"}
            </button>
          </div>
          {showJsonResult ? (
            <pre className="max-h-60 overflow-auto rounded-xl /70 p-3 text-xs  custom-scrollbar" style={{ color: "var(--foreground)" ,  backgroundColor: "var(--surface-base)" }}>
              {JSON.stringify(executionResult, null, 2)}
            </pre>
          ) : executionColumns.length === 0 ? (
            <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>No columns returned.</p>
          ) : (
            <div className="overflow-auto custom-scrollbar">
              <table className="min-w-full text-left text-xs " style={{ color: "var(--foreground-secondary)" }}>
                <thead>
                  <tr>
                    {executionColumns.map((column) => (
                      <th
                        key={column}
                        className="border-b  dark: px-2 py-1 uppercase tracking-normal " style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--muted-foreground)" }}
                      >
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {executionRows.map((row, rowIndex) => (
                    <tr
                      key={`row-${rowIndex}`}
                      className={rowIndex % 2 === 0 ? "bg-[var(--surface-overlay)]" : "bg-[var(--surface-overlay)]"}
                    >
                      {executionColumns.map((column) => (
                        <td key={`${rowIndex}-${column}`} className="px-2 py-1 align-top">
                          <pre className="m-0 text-[12px] " style={{ color: "var(--foreground)" }}>{String(row[column] ?? "")}</pre>
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
        <p className="text-sm " style={{ color: "var(--muted-foreground)" }}>Execute the SQL to see results here.</p>
      )}
      <div className="space-y-3 rounded-2xl border  dark:  p-4" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
        <div className="flex items-center justify-between">
          <p className="text-xs uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>Execution logs</p>
          <span className="text-[10px] uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>
            {execLogs.length} entries
          </span>
        </div>
        {logsLoading ? (
          <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>Loading logs…</p>
        ) : execLogs.length === 0 ? (
          <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>No executions yet.</p>
        ) : (
          <div className="space-y-2">
            {execLogs.map((log) => (
              <button
                key={log.exec_id}
                onClick={() => applyLogParams(log)}
                className="w-full rounded-2xl border  dark: /30 p-3 text-left text-xs  transition hover:" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground-secondary)" ,  backgroundColor: "var(--surface-base)" }}
              >
                <div className="flex items-center justify-between text-[11px] " style={{ color: "var(--muted-foreground)" }}>
                  <span>
                    {log.status.toUpperCase()} · {new Date(log.executed_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}
                  </span>
                  <span>
                    {log.row_count} rows · {log.duration_ms} ms
                  </span>
                </div>
                <p className="mt-1 text-[11px]  dark:" style={{ color: "var(--foreground)" ,  color: "var(--foreground-secondary)" }}>by {log.executed_by ?? "ops-builder"}</p>
                {log.request_params ? (
                  <pre className="mt-2 max-h-20 overflow-auto text-[10px]  custom-scrollbar" style={{ color: "var(--muted-foreground)" }}>
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
        <div className="space-y-4">
          <ErrorBanner
            title="API Definition Errors"
            errors={lastSaveError ? [lastSaveError] : []}
            warnings={statusMessage && statusMessage.includes("Warning") ? [statusMessage] : []}
            onDismiss={() => setLastSaveError(null)}
            autoDismissMs={0}
          />

          <FormSection
            title="API Metadata"
            description="Define the basic information about your API"
            columns={1}
          >
            <FormFieldGroup
              label="API Name"
              required
              help="Use a descriptive name for your API"
            >
              <input
                value={definitionDraft.api_name}
                onChange={(event) =>
                  setDefinitionDraft((prev) => ({ ...prev, api_name: event.target.value }))
                }
                className="w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
                disabled={isSystemScope}
                placeholder="e.g., User Management API"
              />
            </FormFieldGroup>
          </FormSection>

          <FormSection
            title="Endpoint Configuration"
            description="Set the HTTP method and endpoint path"
            columns={2}
          >
            <FormFieldGroup label="HTTP Method" required>
              <select
                value={definitionDraft.method}
                onChange={(event) =>
                  setDefinitionDraft((prev) => ({ ...prev, method: event.target.value as ApiDraft["method"] }))
                }
                className="w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
                disabled={isSystemScope}
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
              </select>
            </FormFieldGroup>
            <FormFieldGroup label="Endpoint Path" required help="/api/users/{id}">
              <input
                value={definitionDraft.endpoint}
                onChange={(event) =>
                  setDefinitionDraft((prev) => ({ ...prev, endpoint: event.target.value }))
                }
                className="w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
                disabled={isSystemScope}
                placeholder="/api/endpoint"
              />
            </FormFieldGroup>
          </FormSection>

          <FormSection title="Description" columns={1}>
            <FormFieldGroup label="API Description" help="Explain what this API does and its purpose">
              <textarea
                value={definitionDraft.description ?? ""}
                onChange={(event) =>
                  setDefinitionDraft((prev) => ({ ...prev, description: event.target.value }))
                }
                className="h-24 w-full rounded-2xl border px-3 py-2 text-sm outline-none transition custom-scrollbar"
                style={{
                  borderColor: "var(--border)",
                  backgroundColor: "var(--surface-base)",
                  color: "var(--foreground)",
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                disabled={isSystemScope}
                placeholder="Describe your API..."
              />
            </FormFieldGroup>
          </FormSection>
          {selectedDiscovered ? (
            <div className="space-y-2 rounded-2xl border p-3 text-[11px]" style={{
              borderColor: "var(--border)",
              backgroundColor: "var(--surface-elevated)",
              color: "var(--foreground)"
            }}>
              <p className="text-[10px] uppercase tracking-normal" style={{ color: "var(--muted-foreground)" }}>Supported actions / constraints</p>
              {selectedDiscovered.summary ? (
                <p className="text-sm" style={{ color: "var(--foreground)" }}>{selectedDiscovered.summary}</p>
              ) : null}
              {discoveredConstraintLines.map((line, index) => (
                <p key={index} className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                  {line}
                </p>
              ))}
              <button
                onClick={() => handleImportDiscoveredEndpoint(selectedDiscovered)}
                className="w-full rounded-2xl border px-3 py-2 text-[11px] font-semibold uppercase tracking-normal transition"
                style={{
                  borderColor: "var(--border)",
                  backgroundColor: "var(--surface-base)",
                  color: "var(--foreground)"
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
              >
                Import to Custom
              </button>
            </div>
          ) : null}

          <FormSection title="Organization" columns={1}>
            <FormFieldGroup
              label="Tags"
              help="Comma-separated tags for organizing APIs (e.g., user-management, analytics)"
            >
              <input
                value={definitionDraft.tags}
                onChange={(event) => setDefinitionDraft((prev) => ({ ...prev, tags: event.target.value }))}
                className="w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
                disabled={isSystemScope}
                placeholder="user, analytics, reporting"
              />
            </FormFieldGroup>
          </FormSection>

          <FormSection
            title="Validation & Policy"
            description="Define parameter schema and runtime policies"
            columns={2}
          >
            <FormFieldGroup
              label="Param Schema (JSON)"
              help="JSON Schema for validating request parameters"
            >
              <textarea
                value={paramSchemaText}
                onChange={(event) => setParamSchemaText(event.target.value)}
                className="h-40 w-full rounded-2xl border px-3 py-2 text-sm outline-none transition custom-scrollbar"
                style={{
                  borderColor: "var(--border)",
                  backgroundColor: "var(--surface-base)",
                  color: "var(--foreground)",
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                disabled={isSystemScope && systemView !== "registered"}
                placeholder='{"type": "object", "properties": {...}}'
              />
            </FormFieldGroup>
            <FormFieldGroup
              label="Runtime Policy (JSON)"
              help="Policy rules for API execution"
            >
              {!isSystemScope || systemView === "registered" ? (
                <textarea
                  value={runtimePolicyText}
                  onChange={(event) => setRuntimePolicyText(event.target.value)}
                  className="h-40 w-full rounded-2xl border px-3 py-2 text-sm outline-none transition custom-scrollbar"
                  style={{
                    borderColor: "var(--border)",
                    backgroundColor: "var(--surface-base)",
                    color: "var(--foreground)",
                  }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
                  onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                  disabled={isSystemScope && systemView !== "registered"}
                  placeholder='{"timeout": 30000}'
                />
              ) : (
                <div className="flex h-40 flex-col justify-center rounded-2xl border p-3 text-[11px]" style={{
                  borderColor: "var(--border)",
                  backgroundColor: "var(--surface-elevated)",
                  color: "var(--muted-foreground)"
                }}>
                  Runtime Policy editing is available only for System {'>'} Registered or Custom APIs.
                </div>
              )}
            </FormFieldGroup>
          </FormSection>

          <FormSection title="Status & Metadata" columns={2}>
            <FormFieldGroup label="Active Status">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={definitionDraft.is_active}
                  onChange={(event) =>
                    setDefinitionDraft((prev) => ({ ...prev, is_active: event.target.checked }))
                  }
                  className="h-4 w-4 rounded   text-sky-400 focus:ring-sky-400" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }}
                  disabled={isSystemScope}
                />
                <span className="text-sm  dark:" style={{ color: "var(--foreground)" ,  color: "var(--foreground-secondary)" }}>Enable this API</span>
              </label>
            </FormFieldGroup>
            <FormFieldGroup
              label="Created By"
              help="Username or service name that created this API"
            >
              <input
                value={definitionDraft.created_by}
                onChange={(event) =>
                  setDefinitionDraft((prev) => ({ ...prev, created_by: event.target.value }))
                }
                className="w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
                placeholder="ops-builder"
                disabled={isSystemScope}
              />
            </FormFieldGroup>
          </FormSection>
        </div>
      )}
      {activeTab === "logic" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>
              Logic ({logicTypeLabels[logicType]})
            </p>
            {!isSystemScope ? (
              <div className="flex flex-wrap items-center gap-2">
                {(["sql", "workflow", "python", "script", "http"] as LogicType[]).map((type) => (
                  <button
                    key={type}
                    onClick={() => setLogicType(type)}
                    disabled={!!selectedId}
                    className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-normal transition ${logicType === type
                      ? "border-sky-500 bg-sky-500/10  dark:"
                      : " dark:  "
                      } ${!!selectedId ? "opacity-40 cursor-not-allowed" : "hover: shadow-sm"}`} style={{ backgroundColor: "var(--surface-base)", color: "var(--foreground)", color: "var(--muted-foreground)", color: "var(--foreground)", borderColor: "var(--border)", borderColor: "var(--border)", borderColor: "var(--border)" }}
                  >
                    {logicTypeLabels[type]}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={handleLogicUndo}
                  className="rounded-full border  px-3 py-1 text-[10px] uppercase tracking-normal  dark: transition hover: disabled:opacity-40" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  color: "var(--foreground-secondary)" }}
                  disabled={logicHistoryIndex <= 0}
                >
                  Undo
                </button>
                <button
                  type="button"
                  onClick={handleLogicRedo}
                  className="rounded-full border  px-3 py-1 text-[10px] uppercase tracking-normal  dark: transition hover: disabled:opacity-40" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  color: "var(--foreground-secondary)" }}
                  disabled={logicHistoryIndex >= logicHistory.length - 1}
                >
                  Redo
                </button>
              </div>
            ) : null}
          </div>
          {logicType === "script" && !isSystemScope ? (
            <label className="text-xs uppercase tracking-normal  flex flex-col gap-2" style={{ color: "var(--muted-foreground)" }}>
              Script language
              <select
                value={scriptLanguage}
                onChange={(event) =>
                  setScriptLanguage(event.target.value as "python" | "javascript")
                }
                className="w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
              >
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
              </select>
            </label>
          ) : null}
          <div
            className={`builder-json-shell rounded-2xl border  dark:  dark: transition-all ${
              logicType === "http" ? "h-auto max-h-[600px] overflow-y-auto" : "h-64 overflow-hidden"
            }`} style={{ backgroundColor: "var(--surface-overlay)", backgroundColor: "var(--background)", borderColor: "var(--border)", borderColor: "var(--border)" }}
          >
            {logicType === "http" ? (
              <div className="p-4">
                <HttpFormBuilder
                  value={httpSpec}
                  onChange={setHttpSpec}
                  isReadOnly={isSystemScope}
                />
              </div>
            ) : logicType === "sql" ? (
              <div className="p-4">
                <SQLQueryBuilder
                  query={logicBody}
                  onChange={setLogicBody}
                  readOnly={isSystemScope}
                />
              </div>
            ) : logicType === "python" ? (
              <div className="p-4">
                <PythonBuilder
                  code={logicBody}
                  onChange={setLogicBody}
                  readOnly={isSystemScope}
                />
              </div>
            ) : logicType === "workflow" ? (
              <div className="p-4">
                <WorkflowBuilder
                  workflow={logicBody}
                  onChange={setLogicBody}
                  readOnly={isSystemScope}
                />
              </div>
            ) : (
              <Editor
                height="100%"
                language={getEditorLanguage(logicType, scriptLanguage)}
                value={logicBody}
                onChange={(value) => setLogicBody(value ?? "")}
                onMount={(editor) => {
                  editorUndoRedoRef.current = editor as unknown as { trigger: (source: string, id: string, payload: unknown) => void };
                }}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  readOnly: isSystemScope,
                }}
              />
            )}
          </div>
          {(bindingValidation.bindings.length > 0 || bindingValidation.errors.length > 0) && (
            <div className="rounded-2xl border  dark:  px-3 py-2 text-[11px]" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
              <p className="" style={{ color: "var(--muted-foreground)" }}>Binding scan</p>
              {bindingValidation.bindings.length > 0 && (
                <p className="mt-1  dark:" style={{ color: "var(--foreground)" ,  color: "var(--foreground-secondary)" }}>
                  Detected: {bindingValidation.bindings.map((binding) => `{{${binding}}}`).join(", ")}
                </p>
              )}
              {bindingValidation.errors.length > 0 && (
                <div className="mt-1 space-y-1 text-rose-300">
                  {bindingValidation.errors.map((error) => (
                    <p key={error}>{error}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
      <div className="flex items-center justify-between mt-6 pt-4 border-t  dark:/60" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" }}>
        <span className={`text-[11px] uppercase tracking-[0.1em] px-3 py-1 rounded-full border ${statusMessage?.toLowerCase().includes("failed") || statusMessage?.toLowerCase().includes("error")
          ? "text-rose-400 border-rose-500/30 bg-rose-500/5 font-semibold"
          : statusMessage && statusMessage.includes("Saved")
            ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/5"
            : "0 border-transparent bg-transparent"
          }`} style={{ color: "var(--foreground)" }}>
          {statusMessage ?? "정의/로직 저장 대기"}
        </span>
        <div className="flex items-center gap-3">
          {activeTab === "logic" && (logicType === "sql" || logicType === "http" || logicType === "script" || logicType === "python") && (
            <button
              onClick={handleDryRunFromEditor}
              className="rounded-full border border-sky-500/30 bg-sky-500/80 px-5 py-2 text-[12px] font-bold uppercase tracking-wider dark: transition hover:bg-sky-400 hover:shadow-[0_0_15px_rgba(14,165,233,0.3)] disabled: disabled:" style={{ color: "var(--foreground)"  ,  color: "var(--foreground)" ,  color: "var(--muted-foreground)" ,  backgroundColor: "var(--surface-elevated)" }}
              disabled={isExecuting}
            >
              {isExecuting ? "Running…" : `Test ${logicTypeLabels[logicType]} (Dry-run)`}
            </button>
          )}
          <button
            onClick={handleSave}
            className="rounded-full border border-emerald-500/30 bg-emerald-500/80 px-6 py-2 text-[12px] font-bold uppercase tracking-wider dark: transition hover:bg-emerald-400 hover:shadow-[0_0_15px_rgba(16,185,129,0.3)] disabled: disabled:" style={{ color: "var(--foreground)"  ,  color: "var(--foreground)" ,  color: "var(--muted-foreground)" ,  backgroundColor: "var(--surface-elevated)" }}
            disabled={isSaving || isSystemScope}
          >
            {isSaving ? "Saving…" : selectedApi ? "Update API" : "Create API"}
          </button>
        </div>
      </div>
      {showLogicResult && activeTab === "logic" && (
        <div className="mt-4 border-t  dark: pt-4" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" }}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>Query Result</span>
            <button
              onClick={() => setShowLogicResult(false)}
              className="text-[10px]  hover: dark:" style={{ color: "var(--foreground)" ,  color: "var(--muted-foreground)" ,  color: "var(--foreground-secondary)" }}
            >
              Close
            </button>
          </div>
          {executionResult ? (
            <div className="space-y-3 rounded-2xl border  dark:  p-4 text-sm " style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground-secondary)" ,  backgroundColor: "var(--surface-overlay)" }}>
              <div className="flex items-center justify-between">
                <div>
                  <p>Rows: {executionResult.row_count}</p>
                  <p>Duration: {executionResult.duration_ms} ms</p>
                </div>
                <button
                  onClick={() => setShowJsonResult((prev) => !prev)}
                  className="text-[10px] uppercase tracking-normal  underline" style={{ color: "var(--muted-foreground)" }}
                >
                  {showJsonResult ? "Hide JSON" : "Show JSON"}
                </button>
              </div>
              {showJsonResult ? (
                <pre className="max-h-60 overflow-auto rounded-xl /70 p-3 text-xs  custom-scrollbar" style={{ color: "var(--foreground)" ,  backgroundColor: "var(--surface-base)" }}>
                  {JSON.stringify(executionResult, null, 2)}
                </pre>
              ) : executionColumns.length === 0 ? (
                <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>No columns returned.</p>
              ) : (
                <div className="overflow-auto custom-scrollbar">
                  <table className="min-w-full text-left text-xs " style={{ color: "var(--foreground-secondary)" }}>
                    <thead>
                      <tr>
                        {executionColumns.map((column) => (
                          <th
                            key={column}
                            className="border-b  dark: px-2 py-1 uppercase tracking-normal " style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--muted-foreground)" }}
                          >
                            {column}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {executionRows.map((row, rowIndex) => (
                        <tr
                          key={`row-${rowIndex}`}
                          className={rowIndex % 2 === 0 ? "bg-[var(--surface-overlay)]" : "bg-[var(--surface-overlay)]"}
                        >
                          {executionColumns.map((column) => (
                            <td key={`${rowIndex}-${column}`} className="px-2 py-1 align-top">
                              <pre className="m-0 text-[12px] " style={{ color: "var(--foreground)" }}>{String(row[column] ?? "")}</pre>
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
            <p className="text-sm " style={{ color: "var(--muted-foreground)" }}>No result available.</p>
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
        <p className="text-[11px] " style={{ color: "var(--muted-foreground)" }}>
          Runtime URL:{" "}
          <span className="font-mono text-[10px] " style={{ color: "var(--foreground-secondary)" }}>
            {`${apiBaseUrl}${selectedApi.endpoint}`}
          </span>
        </p>
      ) : null}
      <label className="text-xs uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>
        Params JSON
        <textarea
          value={testParams}
          onChange={(event) => setTestParams(event.target.value)}
          className="mt-2 h-32 w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500 custom-scrollbar" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
        />
      </label>
      {isWorkflowApi ? (
        <label className="text-xs uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>
          Input JSON (optional)
          <textarea
            value={testInput}
            onChange={(event) => setTestInput(event.target.value)}
            className="mt-2 h-24 w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500 custom-scrollbar" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
          />
        </label>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="text-xs uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>
          Limit
          <input
            type="number"
            min={1}
            max={1000}
            value={testLimit}
            onChange={(event) => setTestLimit(event.target.value)}
            className="mt-2 w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
          />
        </label>
        <label className="text-xs uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>
          Executed by
          <input
            value={executedBy}
            onChange={(event) => setExecutedBy(event.target.value)}
            className="mt-2 w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
            placeholder="ops-builder"
          />
        </label>
        <div className="flex items-end">
          <button
            onClick={handleExecute}
            className="w-full rounded-2xl border dark: bg-sky-500/90 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal dark: transition hover:bg-sky-400 disabled:" style={{ color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-elevated)" }}
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
        <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>
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
              ? "border-sky-500 bg-sky-500/10  dark:"
              : " dark:  "
              }`} style={{ backgroundColor: "var(--surface-base)", color: "var(--foreground)", color: "var(--muted-foreground)", color: "var(--foreground)", borderColor: "var(--border)", borderColor: "var(--border)" }}
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
          <p className="text-xs uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>Metadata (Current Editor)</p>
          <div className="space-y-2 rounded-2xl border  dark:  p-3 text-sm  dark:" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  color: "var(--foreground-secondary)" ,  backgroundColor: "var(--surface-overlay)" }}>
            <p>
              Endpoint: <span className="" style={{ color: "var(--foreground)" }}>{definitionDraft.endpoint || "(new)"}</span>
            </p>
            <p>
              Logic type: <span className="text-sky-400 font-mono">{logicTypeLabels[logicType]}</span>
            </p>
            {selectedApi && (
              <p className="border-t  dark:/60 pt-2 text-[10px] " style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--muted-foreground)" }}>
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
        <h3 className="text-xs uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>API 목록</h3>
        <div className="flex gap-2 text-[10px] uppercase tracking-normal">
          {(["custom"] as ScopeType[])
            .concat(enableSystemApis ? (["system"] as ScopeType[]) : [])
            .map((item) => (
              <button
                key={item}
                onClick={() => setScope(item as ScopeType)}
                className={`rounded-full border px-3 py-1 transition ${scope === item
                  ? "border-sky-500 bg-sky-500/10  dark:"
                  : "  "
                  }`} style={{ backgroundColor: "var(--surface-base)", color: "var(--foreground)", color: "var(--muted-foreground)", color: "var(--foreground)", borderColor: "var(--border)" }}
              >
                {SCOPE_LABELS[item]}
              </button>
            ))}
        </div>
      </div>
      {scope === "system" && enableSystemApis ? (
        <>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[10px] uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>
              <div className="flex items-center gap-2">
                {(["discovered", "registered"] as SystemView[]).map((view) => (
                  <button
                    key={view}
                    onClick={() => setSystemView(view)}
                    className={`rounded-full border px-2 py-1 text-[10px] uppercase tracking-normal transition ${systemView === view
                      ? "border-sky-500 bg-sky-500/10  dark:"
                      : "  "
                      }`} style={{ backgroundColor: "var(--surface-base)", color: "var(--foreground)", color: "var(--muted-foreground)", color: "var(--foreground)", borderColor: "var(--border)" }}
                  >
                    {view}
                  </button>
                ))}
              </div>
            </div>
            {systemView === "discovered" ? (
              <>
                <p className="text-[11px] " style={{ color: "var(--muted-foreground)" }}>Discovered endpoints are read-only.</p>
                <p className="text-[11px] " style={{ color: "var(--muted-foreground)" }}>
                  Discovered from source (OpenAPI). These are not DB-registered APIs.
                </p>
                <div className="text-[10px] uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>
                  Last fetch:{" "}
                  <span className=" dark:" style={{ color: "var(--foreground)" ,  color: "var(--foreground-secondary)" }}>
                    {discoveredFetchAt
                      ? new Date(discoveredFetchAt).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })
                      : "-"}
                  </span>{" "}
                  · Status:{" "}
                  <span className={discoveredFetchStatus === "error" ? "text-rose-300" : "text-[var(--foreground)] dark:text-[var(--foreground-secondary)]"}>
                    {discoveredFetchStatus}
                  </span>
                  {discoveredError ? (
                    <span className="ml-2 text-rose-300">Error: {discoveredError}</span>
                  ) : null}
                </div>
              </>
            ) : (
              <>
                <p className="text-[11px] " style={{ color: "var(--muted-foreground)" }}>Registered APIs are read-only.</p>
                {systemFetchStatus === "error" ? (
                  <div className="rounded-2xl border border-amber-500/60 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200">
                    Server list unavailable. Showing local cache only.
                  </div>
                ) : null}
                <div className="text-[10px] uppercase tracking-normal " style={{ color: "var(--muted-foreground)" }}>
                  Last fetch:{" "}
                  <span className=" dark:" style={{ color: "var(--foreground)" ,  color: "var(--foreground-secondary)" }}>
                    {systemFetchAt
                      ? new Date(systemFetchAt).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })
                      : "-"}
                  </span>{" "}
                  · Status:{" "}
                  <span className={systemFetchStatus === "error" ? "text-rose-300" : "text-[var(--foreground)] dark:text-[var(--foreground-secondary)]"}>
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
                  className="w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
                />
                <button
                  onClick={loadDiscoveredEndpoints}
                  className="ml-2 rounded-full border   px-3 py-2 text-[10px] uppercase tracking-normal  transition hover:" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--muted-foreground)" ,  backgroundColor: "var(--surface-base)" }}
                >
                  Refresh
                </button>
              </div>
              {discoveredError ? <p className="text-xs text-rose-400">{discoveredError}</p> : null}
              <div className="max-h-[420px] overflow-auto rounded-2xl border  dark: /40 custom-scrollbar" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }}>
                <table className="min-w-full table-auto text-left text-xs " style={{ color: "var(--foreground-secondary)" }}>
                  <thead className="sticky top-0 /90" style={{ backgroundColor: "var(--surface-base)" }}>
                    <tr>
                      {["method", "path", "summary", "tags", "source"].map((column) => (
                        <th
                          key={column}
                          className="border-b  dark: px-2 py-2 uppercase tracking-normal  whitespace-nowrap" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--muted-foreground)" }}
                        >
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDiscoveredEndpoints.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-3 py-3 " style={{ color: "var(--muted-foreground)" }}>
                          No discovered endpoints found.
                        </td>
                      </tr>
                    ) : (
                      filteredDiscoveredEndpoints.map((endpoint) => (
                        <tr
                          key={`${endpoint.method}-${endpoint.path}`}
                          className={`cursor-pointer border-b /60 ${selectedDiscovered?.path === endpoint.path &&
                            selectedDiscovered?.method === endpoint.method
                            ? "bg-sky-500/10  dark:"
                            : "hover:"
                            }`} style={{ backgroundColor: "var(--surface-overlay)", color: "var(--foreground)", color: "var(--foreground)", borderColor: "var(--border)" }}
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
                            <span className="rounded-full border  px-2 py-1 text-[10px] uppercase tracking-normal " style={{ borderColor: "var(--border)" ,  color: "var(--muted-foreground)" }}>
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
                  className="w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
                />
                <div className="ml-2 flex items-center gap-2">
                  <button
                    onClick={() => loadApis(selectedId ?? undefined)}
                    className="rounded-full border   px-3 py-2 text-[10px] uppercase tracking-normal  transition hover:" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--muted-foreground)" ,  backgroundColor: "var(--surface-base)" }}
                  >
                    Refresh
                  </button>
                </div>
              </div>
              {systemError ? <p className="text-xs text-rose-400">{systemError}</p> : null}
              <div className="max-h-[420px] overflow-auto rounded-2xl border  dark: /40 custom-scrollbar" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }}>
                <table className="min-w-full table-auto text-left text-xs " style={{ color: "var(--foreground-secondary)" }}>
                  <thead className="sticky top-0 /90" style={{ backgroundColor: "var(--surface-base)" }}>
                    <tr>
                      {["method", "endpoint", "api_name", "tags", "updated_at", "source"].map((column) => (
                        <th
                          key={column}
                          className="border-b  dark: px-2 py-2 uppercase tracking-normal  whitespace-nowrap" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--muted-foreground)" }}
                        >
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredSystemApis.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-3 py-3 " style={{ color: "var(--muted-foreground)" }}>
                          No registered APIs found.
                        </td>
                      </tr>
                    ) : (
                      filteredSystemApis.map((api) => (
                        <tr
                          key={api.api_id}
                          className={`cursor-pointer border-b /60 ${selectedApi?.api_id === api.api_id
                            ? "bg-sky-500/10  dark:"
                            : "hover:"
                            }`} style={{ backgroundColor: "var(--surface-overlay)", color: "var(--foreground)", color: "var(--foreground)", borderColor: "var(--border)" }}
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
                            <span className="rounded-full border  px-2 py-1 text-[10px] uppercase tracking-normal " style={{ borderColor: "var(--border)" ,  color: "var(--muted-foreground)" }}>
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
                  ? "border-sky-500 bg-sky-500/10  dark:"
                  : "  "
                  }`} style={{ backgroundColor: "var(--surface-base)", color: "var(--foreground)", color: "var(--muted-foreground)", color: "var(--foreground)", borderColor: "var(--border)" }}
              >
                {item.label}
              </button>
            ))}
          </div>
          <input
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="검색"
            className="w-full rounded-2xl border dark: dark: px-3 py-2 text-sm dark: outline-none transition focus:border-sky-500" style={{ backgroundColor: "var(--background)", color: "var(--foreground)"  ,  borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-overlay)" }}
          />
          <div className="space-y-2 max-h-[360px] overflow-auto custom-scrollbar">
            {filteredApis.length === 0 ? (
              <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>검색 결과 없음</p>
            ) : (
              filteredApis.map((api) => (
                <button
                  key={api.api_id}
                  onClick={() => setSelectedId(api.api_id)}
                  className={`w-full rounded-2xl border px-3 py-2 text-left text-sm transition flex items-center gap-3 whitespace-nowrap overflow-hidden ${selectedId === api.api_id
                    ? "border-sky-400 bg-sky-500/10  dark:"
                    : " dark:   dark: hover:"
                    }`} style={{ backgroundColor: "var(--surface-base)", color: "var(--foreground)", color: "var(--foreground-secondary)", color: "var(--foreground)", color: "var(--foreground)", borderColor: "var(--border)", borderColor: "var(--border)", borderColor: "var(--border)" }}
                >
                  <div className="flex flex-col flex-1 overflow-hidden">
                    <div className="flex items-center gap-2 overflow-hidden">
                      <span className="text-[10px] uppercase  min-w-8" style={{ color: "var(--muted-foreground)" }}>{api.method}</span>
                      <span className="font-semibold truncate">{api.api_name}</span>
                      {((api.source === "local" && api.api_id !== "applied-draft-temp") || api.api_id.startsWith("local-")) && (
                        <span className="rounded-full border border-amber-500/50 bg-amber-500/10 px-1.5 py-0.2 text-[8px] uppercase tracking-normal text-amber-400">
                          Local
                        </span>
                      )}
                    </div>
                    <span className="text-[10px]  truncate" style={{ color: "var(--muted-foreground)" }}>{api.endpoint}</span>
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
          ? "   cursor-not-allowed"
          : " dark:   hover:"
          }`} style={{ backgroundColor: "var(--surface-overlay)", backgroundColor: "var(--surface-base)", color: "var(--muted-foreground)", color: "var(--muted-foreground)", borderColor: "var(--border)", borderColor: "var(--border)", borderColor: "var(--border)", borderColor: "var(--border)" }}
        disabled={scope === "system"}
      >
        New API
      </button>
    </div>
  );

  const processAssistantDraft = useCallback(
    (messageText: string, isComplete: boolean) => {
      setLastAssistantRaw(messageText);
      const baseDraft = draftApi ?? (selectedApi ? apiToDraft(selectedApi) : buildDraftFromForm());
      const result = parseApiDraft(messageText, baseDraft);
      setLastParseStatus(result.ok ? "success" : "fail");
      setLastParseError(result.error ?? null);

      if (result.ok && result.draft) {
        if (isComplete) {
          recordCopilotMetric("api-manager", "parse_success");
        }
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
          recordCopilotMetric("api-manager", "parse_failure", result.error ?? null);
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
  const copilotBuilderContext = useMemo(
    () => ({
      selected_api: selectedApi
        ? {
            api_id: selectedApi.api_id,
            api_name: selectedApi.api_name,
            method: selectedApi.method,
            endpoint: selectedApi.endpoint,
            logic_type: selectedApi.logic_type,
          }
        : null,
      draft_status: draftStatus,
      active_tab: activeTab,
      form_snapshot: {
        api_name: definitionDraft.api_name,
        method: definitionDraft.method,
        endpoint: definitionDraft.endpoint,
        logic_type: logicType,
      },
    }),
    [activeTab, definitionDraft.api_name, definitionDraft.endpoint, definitionDraft.method, draftStatus, logicType, selectedApi]
  );

  const rightPane = (
    <DraftAssistantPanel
      instructionPrompt={API_MANAGER_COPILOT_INSTRUCTION}
      scenarioFunctions={API_MANAGER_SCENARIO_FUNCTIONS}
      builderContext={copilotBuilderContext}
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
      draftStatusLabels={draftStatusLabels}
      draftStatus={draftStatus}
      draftNotes={draftNotes}
      draftDiff={draftDiff}
      draftApi={draftApi}
      draftTestOk={draftTestOk}
      draftErrors={draftErrors}
      draftWarnings={draftWarnings}
      previewSummary={previewSummary}
      previewJson={previewJson}
      showDebug={showDebug}
      saveTarget={saveTarget}
      lastSaveError={lastSaveError}
      selectedApi={selectedApi}
      lastParseStatus={lastParseStatus}
      lastParseError={lastParseError}
      lastAssistantRaw={lastAssistantRaw}
      onPreviewDraft={handlePreviewDraft}
      onTestDraft={handleTestDraft}
      onApplyDraft={handleApplyDraft}
      onSaveLocalDraft={handleSaveLocalDraft}
    />
  );

  return (
    <div className="api-manager-theme py-6">
      <h1 className="text-2xl font-semibold dark:" style={{ color: "var(--foreground)"  ,  color: "var(--foreground)" }}>API Manager</h1>
      <p className="mb-6 text-sm " style={{ color: "var(--muted-foreground)" }}>
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
