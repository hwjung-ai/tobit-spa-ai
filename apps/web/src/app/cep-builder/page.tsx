"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import BuilderShell from "../../components/builder/BuilderShell";
import BuilderCopilotPanel from "../../components/chat/BuilderCopilotPanel";
import { saveCepWithFallback } from "../../lib/cepBuilderSave";
import Editor from "@monaco-editor/react";
import {
  BasicInfoSection,
  TriggerSection,
  ConditionsSection,
  WindowingSection,
  AggregationSection,
  EnrichmentSection,
  ActionsSection,
  SimulationPanel,
  JsonPreview,
} from "../../components/cep-form-builder";

type CenterTab = "definition" | "definition-form" | "test" | "logs";
type TriggerType = "metric" | "event" | "schedule";

interface CepRule {
  rule_id: string;
  rule_name: string;
  trigger_type: TriggerType;
  trigger_spec: Record<string, unknown>;
  action_spec: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface CepExecLog {
  exec_id: string;
  rule_id: string;
  triggered_at: string;
  status: string;
  duration_ms: number;
  error_message: string | null;
  references: Record<string, unknown>;
}

interface CepDraft {
  rule_name: string;
  description?: string;
  trigger: Record<string, unknown>;
  conditions?: Record<string, unknown>[];
  actions?: Record<string, unknown>[];
  references?: Record<string, unknown>;
}

type DraftStatus = "idle" | "draft_ready" | "previewing" | "testing" | "applied" | "saved" | "outdated" | "error";

const normalizeBaseUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "";

const parseJsonObject = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }
  return JSON.parse(trimmed);
};

const stripCodeFences = (value: string) => {
  const match = value.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (match && match[1]) {
    return match[1].trim();
  }
  return value.trim();
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

const validateCepDraftShape = (draft: CepDraft) => {
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

const parseCepDraft = (text: string) => {
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

const tabOptions: { id: CenterTab; label: string }[] = [
  { id: "definition", label: "JSON Editor" },
  { id: "definition-form", label: "Form Builder" },
  { id: "test", label: "Test" },
  { id: "logs", label: "Logs" },
];

const DRAFT_STORAGE_PREFIX = "cep-builder:draft:";
const FINAL_STORAGE_PREFIX = "cep-builder:rule:";

const draftStatusLabels: Record<DraftStatus, string> = {
  idle: "대기 중",
  draft_ready: "드래프트 준비됨",
  previewing: "미리보기",
  testing: "테스트 중",
  applied: "폼 적용됨",
  saved: "저장됨",
  outdated: "드래프트 오래됨",
  error: "오류 발생",
};

export default function CepBuilderPage() {
  const apiBaseUrl = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  const [rules, setRules] = useState<CepRule[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<CenterTab>("definition");
  const [ruleName, setRuleName] = useState("");
  const [ruleDescription, setRuleDescription] = useState("");
  const [triggerType, setTriggerType] = useState<TriggerType>("schedule");
  const [triggerSpecText, setTriggerSpecText] = useState("{}");
  const [actionSpecText, setActionSpecText] = useState("{}");
  const [isActive, setIsActive] = useState(true);
  const [statusMessage, setStatusMessage] = useState("Select or create a CEP rule.");
  const [statusError, setStatusError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isTriggering, setIsTriggering] = useState(false);
  const [payloadText, setPayloadText] = useState("{}");
  const [simulateResult, setSimulateResult] = useState<Record<string, unknown> | null>(null);
  const [triggerResult, setTriggerResult] = useState<Record<string, unknown> | null>(null);
  const [logs, setLogs] = useState<CepExecLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [draftApi, setDraftApi] = useState<CepDraft | null>(null);
  const [draftStatus, setDraftStatus] = useState<DraftStatus>("idle");
  const [draftNotes, setDraftNotes] = useState<string | null>(null);
  const [draftErrors, setDraftErrors] = useState<string[]>([]);
  const [draftWarnings, setDraftWarnings] = useState<string[]>([]);
  const [draftTestOk, setDraftTestOk] = useState<boolean | null>(null);
  const [draftPreviewJson, setDraftPreviewJson] = useState<string | null>(null);
  const [draftPreviewSummary, setDraftPreviewSummary] = useState<string | null>(null);
  const [lastAssistantRaw, setLastAssistantRaw] = useState("");
  const [lastParseStatus, setLastParseStatus] = useState<"idle" | "success" | "fail">("idle");
  const [lastParseError, setLastParseError] = useState<string | null>(null);
  const [saveTarget, setSaveTarget] = useState<"server" | "local" | null>(null);
  const [lastSaveError, setLastSaveError] = useState<string | null>(null);
  const [formBaselineSnapshot, setFormBaselineSnapshot] = useState<string | null>(null);
  const [appliedDraftSnapshot, setAppliedDraftSnapshot] = useState<string | null>(null);

  // Form mode states
  interface Condition {
    id: string;
    field: string;
    op: string;
    value: string;
  }
  interface Action {
    id: string;
    type: "webhook" | "notify" | "trigger" | "store";
    endpoint?: string;
    method?: "GET" | "POST" | "PUT" | "DELETE";
    channels?: string[];
    message?: string;
  }
  const [formConditions, setFormConditions] = useState<Condition[]>([]);
  const [formConditionLogic, setFormConditionLogic] = useState<"AND" | "OR" | "NOT">("AND");
  const [formActions, setFormActions] = useState<Action[]>([]);
  const [formWindowConfig, setFormWindowConfig] = useState<Record<string, any>>({});
  const [formAggregations, setFormAggregations] = useState<any[]>([]);
  const [formGroupByFields, setFormGroupByFields] = useState<string[]>([]);
  const [formEnrichments, setFormEnrichments] = useState<any[]>([]);

  const draftStorageId = selectedId ?? "new";
  const finalStorageId = selectedId ?? (ruleName.trim() || "new");

  const selectedRule = useMemo(
    () => rules.find((rule) => rule.rule_id === selectedId) ?? null,
    [rules, selectedId]
  );

  const buildCepPayloadFromForm = useCallback(() => {
    let parsedTriggerSpec;
    let parsedActionSpec;
    try {
      parsedTriggerSpec = parseJsonObject(triggerSpecText);
    } catch {
      setStatusError("Trigger spec must be valid JSON.");
      return null;
    }
    try {
      parsedActionSpec = parseJsonObject(actionSpecText);
    } catch {
      setStatusError("Action spec must be valid JSON.");
      return null;
    }
    if (!ruleName.trim()) {
      setStatusError("Rule name is required.");
      return null;
    }
    return {
      rule_name: ruleName.trim(),
      trigger_type: triggerType,
      trigger_spec: parsedTriggerSpec,
      action_spec: parsedActionSpec,
      is_active: isActive,
    };
  }, [triggerSpecText, actionSpecText, ruleName, triggerType, isActive]);

  const buildFormSnapshot = useCallback(() => {
    return JSON.stringify({
      rule_name: ruleName,
      description: ruleDescription,
      trigger_type: triggerType,
      trigger_spec: triggerSpecText,
      action_spec: actionSpecText,
      is_active: isActive,
    });
  }, [ruleName, ruleDescription, triggerType, triggerSpecText, actionSpecText, isActive]);

  const saveCepToServer = useCallback(
    async (payload: Record<string, unknown>) => {
      const target = selectedRule
        ? `${apiBaseUrl}/cep/rules/${selectedRule.rule_id}`
        : `${apiBaseUrl}/cep/rules`;
      const method = selectedRule ? "PUT" : "POST";
      try {
        const response = await fetch(target, {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          return { ok: false, error: data?.detail ?? "Unable to save rule", details: data };
        }
        return { ok: true, data: data?.data?.rule ?? null };
      } catch (error) {
        return { ok: false, error: error instanceof Error ? error.message : "Network error", details: error };
      }
    },
    [apiBaseUrl, selectedRule]
  );

  const actionEndpointLabel = useMemo(() => {
    const spec = selectedRule?.action_spec ?? {};
    const candidate = (spec as Record<string, unknown>).endpoint;
    if (typeof candidate === "string") {
      return candidate;
    }
    return "Configure an action endpoint";
  }, [selectedRule]);

  const loadRules = useCallback(async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/cep/rules`);
      const payload = await response.json();
      setRules(payload.data?.rules ?? []);
      setSelectedId((prev) => {
        if (prev && payload.data?.rules?.some((rule: CepRule) => rule.rule_id === prev)) {
          return prev;
        }
        return payload.data?.rules?.[0]?.rule_id ?? null;
      });
    } catch (error) {
      console.error("Failed to load CEP rules", error);
      setRules([]);
      setSelectedId(null);
    }
  }, [apiBaseUrl]);

  const fetchLogs = useCallback(async () => {
    if (!selectedRule) {
      setLogs([]);
      return;
    }
    setLogsLoading(true);
    try {
      const response = await fetch(`${apiBaseUrl}/cep/rules/${selectedRule.rule_id}/exec-logs?limit=20`);
      const payload = await response.json();
      setLogs(payload.data?.logs ?? []);
    } catch (error) {
      console.error("Failed to load CEP logs", error);
      setLogs([]);
    } finally {
      setLogsLoading(false);
    }
  }, [apiBaseUrl, selectedRule]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  useEffect(() => {
    const key = `${DRAFT_STORAGE_PREFIX}${draftStorageId}`;
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      setDraftApi(null);
      setDraftStatus("idle");
      setDraftNotes(null);
      setDraftTestOk(null);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as CepDraft;
      setDraftApi(parsed);
      setDraftStatus("draft_ready");
      setDraftNotes("미적용 드래프트가 있습니다.");
      setDraftTestOk(null);
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
    if (selectedRule) {
      setRuleName(selectedRule.rule_name);
      setRuleDescription(
        typeof (selectedRule.action_spec as Record<string, unknown>)?.description === "string"
          ? String((selectedRule.action_spec as Record<string, unknown>).description)
          : ""
      );
      setTriggerType(selectedRule.trigger_type);
      setTriggerSpecText(JSON.stringify(selectedRule.trigger_spec ?? {}, null, 2));
      setActionSpecText(JSON.stringify(selectedRule.action_spec ?? {}, null, 2));
      setIsActive(selectedRule.is_active);
      setStatusMessage(
        `Last updated ${new Date(selectedRule.updated_at).toLocaleString("ko-KR", {
          timeZone: "Asia/Seoul",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })}`
      );
      setStatusError(null);
      setSimulateResult(null);
      setTriggerResult(null);
      setPayloadText("{}");
      fetchLogs();
      setFormBaselineSnapshot(null);
      setAppliedDraftSnapshot(null);
    } else {
      setRuleName("");
      setRuleDescription("");
      setTriggerType("schedule");
      setTriggerSpecText("{}");
      setActionSpecText("{}");
      setIsActive(true);
      setStatusMessage("Define a new CEP rule to get started.");
      setLogs([]);
      setFormBaselineSnapshot(buildFormSnapshot());
      setAppliedDraftSnapshot(null);
    }
  }, [selectedRule, fetchLogs, buildFormSnapshot]);

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
  }, [buildFormSnapshot, formBaselineSnapshot, draftApi, appliedDraftSnapshot]);

  const filteredRules = useMemo(() => {
    if (!searchTerm.trim()) {
      return rules;
    }
    const lower = searchTerm.toLowerCase();
    return rules.filter((rule) => rule.rule_name.toLowerCase().includes(lower));
  }, [rules, searchTerm]);

  const applyCepDraftToForm = (draft: CepDraft) => {
    setRuleName(draft.rule_name);
    setRuleDescription(draft.description ?? "");
    const triggerPayload = draft.trigger ?? {};
    const draftTriggerType = (triggerPayload as Record<string, unknown>).type;
    if (draftTriggerType === "metric" || draftTriggerType === "event" || draftTriggerType === "schedule") {
      setTriggerType(draftTriggerType);
    }
    setTriggerSpecText(JSON.stringify(triggerPayload ?? {}, null, 2));
    const actionPayload = {
      actions: draft.actions ?? [],
      conditions: draft.conditions ?? [],
      references: draft.references ?? {},
      description: draft.description ?? "",
    };
    setActionSpecText(JSON.stringify(actionPayload, null, 2));
    setDraftStatus("applied");
    setDraftNotes("드래프트가 폼에 적용되었습니다. 저장 전입니다.");
    setStatusMessage("Draft applied to editor (not saved).");
    setAppliedDraftSnapshot(JSON.stringify(draft));
  };

  useEffect(() => {
    const key = `${FINAL_STORAGE_PREFIX}${finalStorageId}`;
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return;
    }
    try {
      const parsed = JSON.parse(raw) as CepDraft;
      applyCepDraftToForm(parsed);
      setFormBaselineSnapshot(buildFormSnapshot());
      setAppliedDraftSnapshot(null);
      setStatusMessage("로컬 저장된 룰을 불러왔습니다.");
    } catch {
      window.localStorage.removeItem(key);
    }
  }, [finalStorageId, buildFormSnapshot]);

  // JSON → Form 동기화: selectedRule 로드 시 폼 데이터 자동 채우기
  useEffect(() => {
    if (!selectedRule) return;

    // Form Builder 탭에서만 동기화 (JSON Editor는 이미 로드됨)
    if (activeTab !== "definition-form") return;

    // trigger_spec에서 복합 조건 추출
    const triggerSpec = selectedRule.trigger_spec as Record<string, any>;

    if (triggerSpec.conditions && Array.isArray(triggerSpec.conditions)) {
      const conditions = triggerSpec.conditions.map((c: any) => ({
        field: c.field || "",
        op: c.op || "==",
        value: c.value,
      }));
      setFormConditions(conditions);
      setFormConditionLogic(triggerSpec.logic || "AND");
    } else {
      setFormConditions([]);
      setFormConditionLogic("AND");
    }

    // 윈도우 설정 추출
    if (triggerSpec.window_config) {
      setFormWindowConfig(triggerSpec.window_config);
    } else {
      setFormWindowConfig({});
    }

    // 집계 설정 추출
    if (triggerSpec.aggregation) {
      setFormAggregations([triggerSpec.aggregation]);
    } else {
      setFormAggregations([]);
    }

    // 보강 설정 추출
    if (triggerSpec.enrichments && Array.isArray(triggerSpec.enrichments)) {
      setFormEnrichments(triggerSpec.enrichments);
    } else {
      setFormEnrichments([]);
    }

    // 액션 설정 추출
    const actionSpec = selectedRule.action_spec as Record<string, any>;
    if (actionSpec.type === "multi_action" && Array.isArray(actionSpec.actions)) {
      setFormActions(actionSpec.actions);
    } else if (actionSpec) {
      setFormActions([actionSpec]);
    } else {
      setFormActions([]);
    }
  }, [selectedRule, activeTab]);

  const handleSave = async () => {
    setStatusError(null);
    let parsedTriggerSpec;
    let parsedActionSpec;
    try {
      parsedTriggerSpec = parseJsonObject(triggerSpecText);
    } catch {
      setStatusError("Trigger spec must be valid JSON.");
      return;
    }
    try {
      parsedActionSpec = parseJsonObject(actionSpecText);
    } catch {
      setStatusError("Action spec must be valid JSON.");
      return;
    }
    if (!ruleName.trim()) {
      setStatusError("Rule name is required.");
      return;
    }
    const payload = {
      rule_name: ruleName.trim(),
      trigger_type: triggerType,
      trigger_spec: parsedTriggerSpec,
      action_spec: parsedActionSpec,
      is_active: isActive,
    };
    setIsSaving(true);
    try {
      const target = selectedRule
        ? `${apiBaseUrl}/cep/rules/${selectedRule.rule_id}`
        : `${apiBaseUrl}/cep/rules`;
      const method = selectedRule ? "PUT" : "POST";
      const response = await fetch(target, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "Unable to save rule");
      }
      const saved: CepRule = data.data.rule;
      setSelectedId(saved.rule_id);
      setStatusMessage(selectedRule ? "Rule updated." : "Rule created.");
      setSimulateResult(null);
      setTriggerResult(null);
      await loadRules();
    } catch (error) {
      console.error("Save failed", error);
      setStatusError(error instanceof Error ? error.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveFromForm = async () => {
    setStatusError(null);

    if (!ruleName.trim()) {
      setStatusError("Rule name is required.");
      return;
    }

    if (formActions.length === 0) {
      setStatusError("At least one action is required.");
      return;
    }

    // 폼 데이터 구성
    const formData = {
      rule_name: ruleName.trim(),
      description: ruleDescription || null,
      is_active: isActive,
      trigger_type: triggerType,
      trigger_spec: parseJsonObject(triggerSpecText),

      // Form Builder 데이터
      composite_condition:
        formConditions.length > 0
          ? {
              conditions: formConditions.map((c) => ({
                field: c.field || "",
                op: c.op || "==",
                value: c.value,
              })),
              logic: formConditionLogic,
            }
          : null,

      window_config:
        Object.keys(formWindowConfig).length > 0 ? formWindowConfig : null,
      aggregation: formAggregations.length > 0 ? formAggregations[0] : null,
      enrichments: formEnrichments,
      actions: formActions.map((a) => ({
        type: a.type,
        endpoint: a.endpoint,
        method: a.method,
        channels: a.channels,
        message: a.message,
      })),
    };

    setIsSaving(true);
    try {
      const response = await fetch(`${apiBaseUrl}/cep/rules/form`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "Unable to save rule");
      }

      const saved: CepRule = data.data.rule;
      setSelectedId(saved.rule_id);
      setStatusMessage("Rule created from form.");
      setSimulateResult(null);
      setTriggerResult(null);
      await loadRules();
    } catch (error) {
      console.error("Save failed", error);
      setStatusError(error instanceof Error ? error.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  };

  const handleNew = useCallback(() => {
    setSelectedId(null);
    setActiveTab("definition");
    setStatusMessage("Define a new rule here.");
    setStatusError(null);
    setTriggerSpecText("{}");
    setActionSpecText("{}");
    setPayloadText("{}");
    setSimulateResult(null);
    setTriggerResult(null);
    setRuleName("");
    setRuleDescription("");
    setIsActive(true);
    setFormBaselineSnapshot(buildFormSnapshot());
    setAppliedDraftSnapshot(null);
  }, [buildFormSnapshot]);

  const handleSimulate = async () => {
    if (!selectedRule?.rule_id) {
      setStatusError("Select a rule first.");
      return;
    }
    let payload = {};
    try {
      payload = parseJsonObject(payloadText);
    } catch {
      setStatusError("Payload must be valid JSON.");
      return;
    }
    setIsSimulating(true);
    try {
      const response = await fetch(`${apiBaseUrl}/cep/rules/${selectedRule.rule_id}/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ test_payload: payload }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "Simulation failed");
      }
      setSimulateResult(data.data.simulation);
      setStatusMessage("Simulation ready.");
    } catch (error) {
      console.error("Simulation failed", error);
      setStatusError(error instanceof Error ? error.message : "Simulation failed");
    } finally {
      setIsSimulating(false);
    }
  };

  const handleTrigger = async () => {
    if (!selectedRule?.rule_id) {
      setStatusError("Select a rule first.");
      return;
    }
    let payload = {};
    try {
      payload = parseJsonObject(payloadText);
    } catch {
      setStatusError("Payload must be valid JSON.");
      return;
    }
    setIsTriggering(true);
    try {
      const response = await fetch(`${apiBaseUrl}/cep/rules/${selectedRule.rule_id}/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "Trigger failed");
      }
      setTriggerResult(data.data.result);
      setStatusMessage("Manual trigger executed.");
      fetchLogs();
    } catch (error) {
      console.error("Trigger failed", error);
      setStatusError(error instanceof Error ? error.message : "Trigger failed");
    } finally {
      setIsTriggering(false);
    }
  };

  const handlePreviewDraft = () => {
    if (!draftApi) {
      setDraftErrors(["CEP 드래프트가 없습니다."]);
      return;
    }
    setDraftStatus("previewing");
    setDraftPreviewJson(JSON.stringify(draftApi, null, 2));
    setDraftPreviewSummary(draftApi.rule_name);
    setDraftNotes("드래프트를 미리보기로 렌더링합니다.");
  };

  const handleTestDraft = () => {
    if (!draftApi) {
      setDraftErrors(["CEP 드래프트가 없습니다."]);
      return;
    }
    setDraftStatus("testing");
    const errors: string[] = [];
    if (!draftApi.rule_name.trim()) {
      errors.push("rule_name은 필수입니다.");
    }
    if (!draftApi.trigger || typeof draftApi.trigger !== "object") {
      errors.push("trigger는 JSON 객체여야 합니다.");
    }
    if (!Array.isArray(draftApi.actions)) {
      errors.push("actions 배열이 필요합니다.");
    }
    setDraftErrors(errors);
    setDraftWarnings([]);
    setDraftTestOk(errors.length === 0);
    setDraftNotes(errors.length === 0 ? "테스트 통과" : "테스트 실패");
    setDraftStatus(errors.length === 0 ? "draft_ready" : "error");
  };

  const handleApplyDraft = () => {
    if (!draftApi) {
      setDraftErrors(["CEP 드래프트가 없습니다."]);
      return;
    }
    if (draftTestOk !== true) {
      setDraftErrors(["테스트를 통과한 뒤 적용할 수 있습니다."]);
      return;
    }
    applyCepDraftToForm(draftApi);
    setDraftErrors([]);
    setDraftWarnings([]);
  };

  const handleSaveDraft = () => {
    if (!draftApi) {
      setDraftErrors(["CEP 드래프트가 없습니다."]);
      return;
    }
    if (draftTestOk !== true) {
      setDraftErrors(["테스트를 통과한 뒤 저장할 수 있습니다."]);
      return;
    }
    const payload = buildCepPayloadFromForm();
    if (!payload) {
      return;
    }
    const storageKey = `${FINAL_STORAGE_PREFIX}${finalStorageId}`;
    setIsSaving(true);
    setSaveTarget(null);
    setLastSaveError(null);
    saveCepWithFallback({
      payload,
      saveCepToServer,
      storage: window.localStorage,
      storageKey,
    })
      .then(async (result) => {
        setSaveTarget(result.target as "server" | "local" | null);
        if (result.target === "server") {
          setStatusMessage("Saved to server.");
          setDraftNotes("서버에 저장되었습니다.");
          const saved = result.data as CepRule | null;
          if (saved?.rule_id) {
            setSelectedId(saved.rule_id);
            await loadRules();
          } else {
            await loadRules();
          }
          window.localStorage.removeItem(storageKey);
        } else {
          setStatusMessage("Saved locally (server unavailable).");
          setDraftNotes("서버 저장 실패로 로컬에 저장했습니다.");
        }
        setDraftApi(null);
        setDraftStatus("saved");
        setDraftTestOk(null);
          setFormBaselineSnapshot(buildFormSnapshot());
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

  const definitionContent = (
    <div className="space-y-4">
      <div className="flex flex-col gap-2">
        <span className="text-xs uppercase tracking-wider text-slate-500">Rule name</span>
        <input
          value={ruleName}
          onChange={(event) => setRuleName(event.target.value)}
          className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
        />
      </div>
      <div className="flex flex-col gap-2">
        <span className="text-xs uppercase tracking-wider text-slate-500">Description</span>
        <textarea
          value={ruleDescription}
          onChange={(event) => setRuleDescription(event.target.value)}
          className="h-20 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
        />
      </div>
      <div className="flex items-center gap-1 text-xs uppercase tracking-wider text-slate-500">
        {(["metric", "event", "schedule"] as TriggerType[]).map((type) => (
          <button
            key={type}
            onClick={() => setTriggerType(type)}
            className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-wider transition ${triggerType === type
              ? "border-sky-500 bg-sky-500/10 text-white"
              : "border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-600"
              }`}
          >
            {type}
          </button>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Trigger spec (JSON)</p>
          <div className="builder-json-shell h-72 resize-y overflow-auto rounded-2xl border border-slate-800 bg-slate-950/60">
            <Editor
              height="100%"
              defaultLanguage="json"
              value={triggerSpecText}
              onChange={(value) => setTriggerSpecText(value ?? "")}
              theme="vs-dark"
              options={{ minimap: { enabled: false }, fontSize: 13, automaticLayout: true }}
            />
          </div>
        </div>
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Action spec (JSON)</p>
          <div className="builder-json-shell h-72 resize-y overflow-auto rounded-2xl border border-slate-800 bg-slate-950/60">
            <Editor
              height="100%"
              defaultLanguage="json"
              value={actionSpecText}
              onChange={(value) => setActionSpecText(value ?? "")}
              theme="vs-dark"
              options={{ minimap: { enabled: false }, fontSize: 13, automaticLayout: true }}
            />
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-3 text-sm text-white">
        <span className="text-[11px] uppercase tracking-wider text-slate-500">
          {statusMessage}
        </span>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="rounded-2xl border border-slate-800 bg-emerald-500/80 px-4 py-2 text-[12px] font-semibold uppercase tracking-wider text-white transition hover:bg-emerald-400 disabled:bg-slate-700"
        >
          {isSaving ? "Saving…" : selectedRule ? "Update rule" : "Create rule"}
        </button>
      </div>
      <label className="flex items-center gap-2 text-xs text-slate-500">
        <input
          type="checkbox"
          checked={isActive}
          onChange={(event) => setIsActive(event.target.checked)}
          className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-sky-400 focus:ring-sky-400"
        />
        <span className="uppercase tracking-wider">Active rule</span>
      </label>
      {statusError ? <p className="text-xs text-rose-400">{statusError}</p> : null}
    </div>
  );

  const formDefinitionContent = (
    <div className="max-h-[600px] overflow-y-auto space-y-4">
      <BasicInfoSection
        ruleName={ruleName}
        description={ruleDescription}
        isActive={isActive}
        onRuleNameChange={setRuleName}
        onDescriptionChange={setRuleDescription}
        onActiveChange={setIsActive}
      />

      <TriggerSection
        triggerType={triggerType as any}
        triggerSpec={parseJsonObject(triggerSpecText)}
        onTriggerTypeChange={(type) => {
          setTriggerType(type);
          setTriggerSpecText("{}");
        }}
        onTriggerSpecChange={(spec) => setTriggerSpecText(JSON.stringify(spec, null, 2))}
      />

      <ConditionsSection
        conditions={formConditions}
        logic={formConditionLogic}
        onConditionsChange={setFormConditions}
        onLogicChange={setFormConditionLogic}
      />

      <WindowingSection
        windowConfig={formWindowConfig}
        onWindowConfigChange={setFormWindowConfig}
      />

      <AggregationSection
        aggregations={formAggregations}
        groupByFields={formGroupByFields}
        onAggregationsChange={setFormAggregations}
        onGroupByChange={setFormGroupByFields}
      />

      <EnrichmentSection
        enrichments={formEnrichments}
        onEnrichmentsChange={setFormEnrichments}
      />

      <ActionsSection
        actions={formActions}
        onActionsChange={setFormActions}
      />

      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
        <div className="flex items-center justify-between cursor-pointer hover:bg-slate-900/40 p-2 rounded-lg">
          <h3 className="text-sm font-semibold text-white">JSON 미리보기</h3>
        </div>
        <div className="mt-3">
          <JsonPreview
            data={{
              rule_name: ruleName,
              description: ruleDescription,
              is_active: isActive,
              trigger_type: triggerType,
              trigger_spec: parseJsonObject(triggerSpecText),
              ...(formConditions.length > 0 && {
                composite_condition: {
                  conditions: formConditions.map((c) => ({
                    field: c.field,
                    op: c.op,
                    value: c.value,
                  })),
                  logic: formConditionLogic,
                },
              }),
              ...(Object.keys(formWindowConfig).length > 0 && {
                window_config: formWindowConfig,
              }),
              actions: formActions.map((a) => ({
                type: a.type,
                endpoint: a.endpoint,
                method: a.method,
                channels: a.channels,
                message: a.message,
              })),
            }}
            title="생성되는 규칙 JSON"
            copyable={true}
          />
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={activeTab === "definition-form" ? handleSaveFromForm : handleSave}
          disabled={isSaving || !ruleName.trim() || formActions.length === 0}
          className="flex-1 rounded-lg border border-emerald-500/50 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? "저장 중..." : selectedRule ? "규칙 수정" : "규칙 생성"}
        </button>
      </div>
      {statusError ? <p className="text-xs text-rose-400">{statusError}</p> : null}
    </div>
  );

  const testContent = (
    <div className="space-y-4">
      <p className="text-[11px] uppercase tracking-wider text-slate-500">
        Action endpoint:&nbsp;
        <span className="font-mono text-[10px] text-slate-200">{actionEndpointLabel}</span>
      </p>
      <div className="flex flex-col gap-2">
        <span className="text-xs uppercase tracking-wider text-slate-500">Payload</span>
        <textarea
          value={payloadText}
          onChange={(event) => setPayloadText(event.target.value)}
          className="h-32 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
        />
      </div>
      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleSimulate}
          className="rounded-2xl border border-slate-800 bg-sky-500/90 px-4 py-2 text-[12px] font-semibold uppercase tracking-wider text-white transition hover:bg-sky-400 disabled:bg-slate-700"
          disabled={!selectedRule || isSimulating}
        >
          {isSimulating ? "Simulating…" : "Simulate"}
        </button>
        <button
          onClick={handleTrigger}
          className="rounded-2xl border border-slate-800 bg-emerald-500/80 px-4 py-2 text-[12px] font-semibold uppercase tracking-wider text-white transition hover:bg-emerald-400 disabled:bg-slate-700"
          disabled={!selectedRule || isTriggering}
        >
          {isTriggering ? "Triggering…" : "Manual trigger"}
        </button>
      </div>
      {statusError ? <p className="text-xs text-rose-400">{statusError}</p> : null}
    </div>
  );

  const logsContent = (
    <div className="space-y-2 max-h-[420px] overflow-auto">
      {logsLoading ? (
        <p className="text-xs text-slate-400">Loading logs…</p>
      ) : logs.length === 0 ? (
        <p className="text-xs text-slate-400">No executions yet.</p>
      ) : (
        logs.map((log) => (
          <div
            key={log.exec_id}
            className="rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-xs text-slate-200"
          >
            <div className="flex items-center justify-between text-[11px] text-slate-500">
              <span>{new Date(log.triggered_at).toLocaleString("ko-KR")}</span>
              <span
                className={`rounded-full border px-2 py-0.5 uppercase tracking-wider ${log.status === "success"
                  ? "border-emerald-400 text-emerald-300"
                  : log.status === "dry_run"
                    ? "border-slate-500 text-slate-300"
                    : "border-rose-500 text-rose-300"
                  }`}
              >
                {log.status}
              </span>
            </div>
            <p className="mt-1 text-[12px] text-slate-300">
              Duration {log.duration_ms} ms
            </p>
            {log.error_message ? (
              <p className="mt-1 text-[10px] text-rose-400">Error: {log.error_message}</p>
            ) : null}
          </div>
        ))
      )}
    </div>
  );

  const centerTop = (
    <div className="space-y-4">
      <div className="flex gap-3">
        {tabOptions.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-wider ${activeTab === tab.id
              ? "border-sky-500 bg-sky-500/10 text-white"
              : "border-slate-800 bg-slate-950 text-slate-400"
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {activeTab === "definition"
        ? definitionContent
        : activeTab === "definition-form"
          ? formDefinitionContent
          : activeTab === "test"
            ? testContent
            : logsContent}
    </div>
  );

  const centerBottom = (
    <div className="space-y-3">
      {activeTab === "definition" || activeTab === "definition-form" ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3 text-xs text-slate-200">
          <p className="text-[11px] uppercase tracking-wider text-slate-500">Metadata</p>
          {selectedRule ? (
            <div className="mt-2 space-y-1 text-[11px] text-slate-400">
              <p>Trigger type: {selectedRule.trigger_type}</p>
              <p>Last updated: {new Date(selectedRule.updated_at).toLocaleString("ko-KR")}</p>
            </div>
          ) : (
            <p className="text-xs text-slate-500">Select a rule to see its metadata.</p>
          )}
        </div>
      ) : activeTab === "test" ? (
        <div className="space-y-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-xs text-slate-200">
            <p className="text-[11px] uppercase tracking-wider text-slate-500">Simulation result</p>
            <pre className="mt-2 max-h-40 overflow-auto rounded-xl bg-slate-950/60 p-3 text-[11px] text-slate-200">
              {simulateResult ? JSON.stringify(simulateResult, null, 2) : "Run a simulation to inspect the payload."}
            </pre>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-xs text-slate-200">
            <p className="text-[11px] uppercase tracking-wider text-slate-500">Manual trigger result</p>
            <pre className="mt-2 max-h-40 overflow-auto rounded-xl bg-slate-950/60 p-3 text-[11px] text-slate-200">
              {triggerResult ? JSON.stringify(triggerResult, null, 2) : "Trigger once to record an execution log."}
            </pre>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-xs text-slate-200">
          <p className="text-[11px] uppercase tracking-wider text-slate-500">Logs</p>
          <p className="mt-2 text-[11px] text-slate-400">
            Click reload to refresh logs or trigger a rule to write entries.
          </p>
        </div>
      )
      }
    </div >
  );

  const leftPane = (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-wider text-slate-500">CEP rules</p>
        <button
          onClick={handleNew}
          className="text-[10px] uppercase tracking-wider text-slate-400 underline"
        >
          New
        </button>
      </div>
      <input
        value={searchTerm}
        onChange={(event) => setSearchTerm(event.target.value)}
        placeholder="Search rules"
        className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
      />
      <div className="space-y-2 max-h-[360px] overflow-y-auto">
        {filteredRules.length === 0 ? (
          <p className="text-xs text-slate-500">No rules found.</p>
        ) : (
          filteredRules.map((rule) => (
            <button
              key={rule.rule_id}
              onClick={() => {
                setSelectedId(rule.rule_id);
                setActiveTab("definition");
              }}
              className={`w-full rounded-2xl border px-3 py-2 text-left text-sm transition ${selectedId === rule.rule_id
                ? "border-sky-400 bg-sky-500/10 text-white"
                : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-600"
                }`}
            >
              <p className="font-semibold">{rule.rule_name}</p>
              <p className="text-[10px] uppercase tracking-wider text-slate-500">{rule.trigger_type}</p>
            </button>
          ))
        )}
      </div>
    </div>
  );

  const COPILOT_INSTRUCTION = `
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

  const processAssistantDraft = useCallback(
    (messageText: string) => {
      setLastAssistantRaw(messageText);
      const result = parseCepDraft(messageText);
      setLastParseStatus(result.ok ? "success" : "fail");
      setLastParseError(result.error ?? null);
      if (result.ok && result.draft) {
        setDraftApi(result.draft);
        setDraftStatus("draft_ready");
        setDraftNotes((prev) => prev ?? "CEP 드래프트가 준비되었습니다.");
        setDraftErrors([]);
        setDraftWarnings([]);
        setDraftTestOk(null);
        setDraftPreviewJson(JSON.stringify(result.draft, null, 2));
        setDraftPreviewSummary(result.draft.rule_name);
      } else {
        setDraftApi(null);
        setDraftPreviewJson(null);
        setDraftPreviewSummary(null);
        setDraftStatus("error");
        setDraftNotes(result.error ?? "CEP 드래프트를 해석할 수 없습니다.");
        setDraftTestOk(false);
      }
    },
    []
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

  const rightPane = (
    <div className="space-y-4 max-h-[80vh] overflow-y-auto pr-1">
      <BuilderCopilotPanel
        builderSlug="cep-builder"
        instructionPrompt={COPILOT_INSTRUCTION}
        onAssistantMessage={handleAssistantMessage}
        onAssistantMessageComplete={handleAssistantMessageComplete}
        inputPlaceholder="CEP 룰 드래프트를 설명해 주세요..."
      />
      <div className="space-y-3 rounded-3xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-wider text-slate-500">Draft status</span>
          <span className="text-sm font-semibold text-white">
            {draftStatusLabels[draftStatus] ?? draftStatus}
          </span>
        </div>
        {draftNotes ? <p className="text-sm text-slate-300">{draftNotes}</p> : null}
        {draftStatus === "outdated" ? (
          <div className="rounded-2xl border border-amber-500/60 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200">
            Draft is outdated. Apply again or regenerate.
          </div>
        ) : null}
        <div className="sticky bottom-0 w-full bg-slate-950/80 pt-3">
          <div className="grid gap-2 sm:grid-cols-2">
            <button
              onClick={handlePreviewDraft}
              className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-white transition hover:border-sky-500"
            >
              Preview
            </button>
            <button
              onClick={handleTestDraft}
              className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-white transition hover:border-emerald-400"
            >
              Test
            </button>
            <button
              onClick={handleApplyDraft}
              className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-white transition hover:border-indigo-400"
              disabled={!draftApi || draftTestOk !== true}
            >
              Apply
            </button>
            <button
              onClick={handleSaveDraft}
              className="rounded-2xl border border-slate-800 bg-emerald-500/70 px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-white transition hover:bg-emerald-400"
              disabled={!draftApi || draftTestOk !== true}
            >
              Save
            </button>
          </div>
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
        {draftPreviewSummary && draftPreviewJson ? (
          <div className="space-y-2 rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-[11px] text-slate-200">
            <p className="text-xs uppercase tracking-wider text-slate-500">Preview</p>
            <p className="text-sm text-white">{draftPreviewSummary}</p>
            <pre className="max-h-48 overflow-auto rounded-xl bg-slate-900/50 p-2 text-[11px] text-slate-300">
              {draftPreviewJson}
            </pre>
          </div>
        ) : null}
        <details className="rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-[11px] text-slate-300">
          <summary className="cursor-pointer text-xs uppercase tracking-wider text-slate-400">
            Debug
          </summary>
          <div className="mt-2 space-y-1">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">
              Save target: {saveTarget ?? "none"}
            </p>
            {lastSaveError ? <p className="text-[11px] text-rose-300">Save error: {lastSaveError}</p> : null}
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Selected rule</p>
            <p className="text-[11px] text-slate-200">
              {selectedRule ? `${selectedRule.rule_name} (${selectedRule.rule_id})` : "새 룰"}
            </p>
            <p className="text-[10px] uppercase tracking-wider text-slate-500">
              Parse status: {lastParseStatus}
            </p>
            {lastParseError ? <p className="text-[11px] text-rose-300">Error: {lastParseError}</p> : null}
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Last assistant raw</p>
            <pre className="max-h-32 overflow-auto rounded-xl bg-slate-900/60 p-2 text-[10px] text-slate-200">
              {lastAssistantRaw || "없음"}
            </pre>
            {draftApi ? (
              <>
                <p className="text-[10px] uppercase tracking-wider text-slate-500">Draft JSON</p>
                <pre className="max-h-32 overflow-auto rounded-xl bg-slate-900/60 p-2 text-[10px] text-slate-200">
                  {JSON.stringify(draftApi, null, 2)}
                </pre>
              </>
            ) : null}
          </div>
        </details>
      </div>
    </div>
  );

  return (
    <div className="py-6 tracking-tight builder-shell builder-text">
      <h1 className="text-2xl font-semibold text-white">CEP Builder</h1>
      <p className="mb-6 text-sm text-slate-400">
        Define, simulate, and trigger complex CEP rules that orchestrate runtime APIs.
      </p>
      <BuilderShell leftPane={leftPane} centerTop={centerTop} centerBottom={centerBottom} rightPane={rightPane} />
    </div>
  );
}
