"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared";
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
import type {
  CenterTab,
  TriggerType,
  CepRule,
  CepExecLog,
  CepDraft,
  DraftStatus,
  Condition,
  Action,
} from "../../lib/cep-builder/types";
import {
  normalizeBaseUrl,
  parseJsonObject,
  parseCepDraft,
  tabOptions,
  DRAFT_STORAGE_PREFIX,
  FINAL_STORAGE_PREFIX,
  draftStatusLabels,
  COPILOT_INSTRUCTION,
  computeCepDraftDiff,
  CEP_COPILOT_EXAMPLE_PROMPTS,
} from "../../lib/cep-builder/utils";
import { recordCopilotMetric } from "../../lib/copilot/metrics";

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
  const [draftDiff, setDraftDiff] = useState<string[] | null>(null);
  const [draftHistory, setDraftHistory] = useState<
    Array<{ id: string; createdAt: string; draft: CepDraft }>
  >([]);
  const [selectedCompareDraftId, setSelectedCompareDraftId] = useState<string | null>(null);
  const [lastAssistantRaw, setLastAssistantRaw] = useState("");
  const [lastParseStatus, setLastParseStatus] = useState<"idle" | "success" | "fail">("idle");
  const [lastParseError, setLastParseError] = useState<string | null>(null);
  const [saveTarget, setSaveTarget] = useState<"server" | "local" | null>(null);
  const [lastSaveError, setLastSaveError] = useState<string | null>(null);
  const [formBaselineSnapshot, setFormBaselineSnapshot] = useState<string | null>(null);
  const [appliedDraftSnapshot, setAppliedDraftSnapshot] = useState<string | null>(null);

  // Form mode states
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
    [rules, selectedId],
  );

  const convertRuleToDraft = useCallback((rule: CepRule): CepDraft => {
    const trigger = rule.trigger_spec ?? {};
    const actionSpec = rule.action_spec ?? {};
    const actionCandidates = Array.isArray((actionSpec as Record<string, unknown>).actions)
      ? ((actionSpec as Record<string, unknown>).actions as Record<string, unknown>[])
      : [actionSpec as Record<string, unknown>];
    const validActions = actionCandidates.filter((item) => Object.keys(item ?? {}).length > 0);
    return {
      rule_name: rule.rule_name,
      description: typeof actionSpec.description === "string" ? actionSpec.description : "",
      trigger,
      conditions: Array.isArray((trigger as Record<string, unknown>).conditions)
        ? ((trigger as Record<string, unknown>).conditions as Record<string, unknown>[])
        : [],
      enrichments: Array.isArray((trigger as Record<string, unknown>).enrichments)
        ? ((trigger as Record<string, unknown>).enrichments as Record<string, unknown>[])
        : [],
      actions: validActions,
      references:
        typeof (actionSpec as Record<string, unknown>).references === "object"
          ? ((actionSpec as Record<string, unknown>).references as Record<string, unknown>)
          : {},
    };
  }, []);

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
        return {
          ok: false,
          error: error instanceof Error ? error.message : "Network error",
          details: error,
        };
      }
    },
    [apiBaseUrl, selectedRule],
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
      const response = await fetch(
        `${apiBaseUrl}/cep/rules/${selectedRule.rule_id}/exec-logs?limit=20`,
      );
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
          : "",
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
        })}`,
      );
      setStatusError(null);
      setSimulateResult(null);
      setTriggerResult(null);
      setPayloadText("{}");
      fetchLogs();
      setFormBaselineSnapshot(null);
      setAppliedDraftSnapshot(null);
      setSelectedCompareDraftId(null);
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
      setSelectedCompareDraftId(null);
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

  useEffect(() => {
    if (!draftApi) {
      setDraftDiff(null);
      return;
    }
    const baseline = selectedRule ? convertRuleToDraft(selectedRule) : null;
    const diffSummary = computeCepDraftDiff(draftApi, baseline);
    setDraftDiff(diffSummary);
  }, [convertRuleToDraft, draftApi, selectedRule]);

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
    if (
      draftTriggerType === "metric" ||
      draftTriggerType === "event" ||
      draftTriggerType === "schedule" ||
      draftTriggerType === "anomaly"
    ) {
      setTriggerType(draftTriggerType);
    }
    setTriggerSpecText(JSON.stringify(triggerPayload ?? {}, null, 2));
    const actionPayload = {
      actions: (draft.actions ?? []).map((a: Record<string, unknown>) => ({
        ...a,
        id: (a.id as string) || `action-${Math.random().toString(36).substr(2, 9)}`,
      })),
      conditions: (draft.conditions ?? []).map((c: Record<string, unknown>) => ({
        ...c,
        id: (c.id as string) || `cond-${Math.random().toString(36).substr(2, 9)}`,
      })),
      enrichments: (draft.enrichments ?? []).map((e: Record<string, unknown>) => ({
        ...e,
        id: (e.id as string) || `enrich-${Math.random().toString(36).substr(2, 9)}`,
      })),
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
    const triggerSpec = selectedRule.trigger_spec as Record<string, unknown>;

    if (triggerSpec.conditions && Array.isArray(triggerSpec.conditions)) {
      const conditions = (triggerSpec.conditions as Record<string, unknown>[]).map((c) => ({
        id: (c.id as string) || `cond-${Math.random().toString(36).substr(2, 9)}`,
        field: (c.field as string) || "",
        op: (c.op as string) || "==",
        value: String(c.value ?? ""),
      }));
      setFormConditions(conditions);
      setFormConditionLogic((triggerSpec.logic as "AND" | "OR" | "NOT") || "AND");
    } else {
      setFormConditions([]);
      setFormConditionLogic("AND");
    }

    // 윈도우 설정 추출
    if (triggerSpec.window_config) {
      setFormWindowConfig(triggerSpec.window_config as Record<string, any>);
    } else {
      setFormWindowConfig({});
    }

    // 집계 설정 추출
    if (triggerSpec.aggregation && typeof triggerSpec.aggregation === "object") {
      setFormAggregations([
        {
          ...(triggerSpec.aggregation as Record<string, unknown>),
          id:
            ((triggerSpec.aggregation as Record<string, unknown>).id as string) ||
            `agg-${Math.random().toString(36).substr(2, 9)}`,
        },
      ]);
    } else {
      setFormAggregations([]);
    }

    // 보강 설정 추출
    if (triggerSpec.enrichments && Array.isArray(triggerSpec.enrichments)) {
      setFormEnrichments(
        (triggerSpec.enrichments as Record<string, unknown>[]).map((e) => ({
          ...e,
          id: (e.id as string) || `enrich-${Math.random().toString(36).substr(2, 9)}`,
        })),
      );
    } else {
      setFormEnrichments([]);
    }

    // 액션 설정 추출
    const actionSpec = selectedRule.action_spec as Record<string, unknown>;
    if (actionSpec.type === "multi_action" && Array.isArray(actionSpec.actions)) {
      setFormActions(
        (actionSpec.actions as Record<string, unknown>[]).map((a) => ({
          ...a,
          id: (a.id as string) || `action-${Math.random().toString(36).substr(2, 9)}`,
          type: (a.type as Action["type"]) || "webhook",
        })) as Action[],
      );
    } else if (actionSpec && Object.keys(actionSpec).length > 0) {
      setFormActions([
        {
          ...actionSpec,
          id: actionSpec.id || `action-${Math.random().toString(36).substr(2, 9)}`,
        } as unknown as Action,
      ]);
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

      window_config: Object.keys(formWindowConfig).length > 0 ? formWindowConfig : null,
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

  const handleTestDraftWithSimulation = async () => {
    if (!draftApi) {
      setDraftErrors(["CEP 드래프트가 없습니다."]);
      return;
    }
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

    if (errors.length > 0) {
      setDraftErrors(errors);
      setDraftWarnings([]);
      setDraftTestOk(false);
      setDraftNotes("규격 테스트 실패 (시뮬레이션 생략)");
      setDraftStatus("error");
      return;
    }

    setDraftStatus("testing");
    setDraftNotes("실제 시뮬레이션 테스트 중...");

    try {
      // 드래프트 시뮬레이션 API 호출
      const payload = {
        rule_name: draftApi.rule_name,
        trigger_type: draftApi.trigger?.type || "schedule",
        trigger_spec: draftApi.trigger || {},
        action_spec: {
          actions: draftApi.actions || [],
          references: draftApi.references || {},
        },
        is_active: true,
      };

      const response = await fetch(`${apiBaseUrl}/cep/rules/simulate-draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.message || "시뮬레이션 실패");
      }

      setSimulateResult(data.data.simulation);
      setDraftNotes("실제 시뮬레이션 테스트 성공! 결과를 확인하세요.");
      setDraftTestOk(true);
      setDraftStatus("draft_ready");
    } catch (err) {
      const message = err instanceof Error ? err.message : "시뮬레이션 오류";
      setDraftErrors([message]);
      setDraftNotes("실제 시뮬레이션 테스트 실패");
      setDraftTestOk(false);
      setDraftStatus("error");
    }
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
        <span className="cep-builder-label">Rule name</span>
        <input
          value={ruleName}
          onChange={(event) => setRuleName(event.target.value)}
          className="cep-builder-input"
        />
      </div>
      <div className="flex flex-col gap-2">
        <span className="cep-builder-label">Description</span>
        <textarea
          value={ruleDescription}
          onChange={(event) => setRuleDescription(event.target.value)}
          className="cep-builder-textarea h-20"
        />
      </div>
      <div className="flex items-center gap-1">
        {(["metric", "event", "schedule", "anomaly"] as TriggerType[]).map((type) => (
          <button
            key={type}
            onClick={() => setTriggerType(type)}
            className={cn(
              "cep-builder-tab text-tiny",
              triggerType === type && "cep-builder-tab-active",
            )}
          >
            {type}
          </button>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <p className="cep-builder-label">Trigger spec (JSON)</p>
          <div className="cep-builder-json-preview builder-json-shell h-72">
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
          <p className="cep-builder-label">Action spec (JSON)</p>
          <div className="cep-builder-json-preview builder-json-shell h-72">
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
      <div className="cep-builder-status-box">
        <span className="cep-builder-label">{statusMessage}</span>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="br-btn border px-4 py-2 text-xs font-semibold uppercase tracking-wider transition bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-40 dark:bg-emerald-700 dark:hover:bg-emerald-600"
        >
          {isSaving ? "Saving…" : selectedRule ? "Update rule" : "Create rule"}
        </button>
      </div>
      <label className="cep-builder-checkbox-label">
        <input
          type="checkbox"
          checked={isActive}
          onChange={(event) => setIsActive(event.target.checked)}
          className="cep-builder-checkbox"
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

      <EnrichmentSection enrichments={formEnrichments} onEnrichmentsChange={setFormEnrichments} />

      <ActionsSection actions={formActions} onActionsChange={setFormActions} />

      <div className="cep-builder-status-box p-4">
        <div
          className="flex items-center justify-between cursor-pointer p-2 br-section"
          style={{ backgroundColor: "var(--surface-base)" }}
        >
          <h3 className="section-title">JSON 미리보기</h3>
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
      <p className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
        Action endpoint:&nbsp;
        <span className="font-mono text-tiny text-slate-500 dark:text-slate-400">
          {actionEndpointLabel}
        </span>
      </p>
      <div className="flex flex-col gap-2">
        <span className="cep-builder-label">Payload</span>
        <textarea
          value={payloadText}
          onChange={(event) => setPayloadText(event.target.value)}
          className="h-32 w-full cep-builder-textarea"
        />
      </div>
      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleSimulate}
          className="br-btn border px-4 py-2 text-xs font-semibold uppercase tracking-wider transition bg-sky-600 text-white hover:bg-sky-500 disabled:opacity-40 dark:bg-sky-700 dark:hover:bg-sky-600"
          disabled={!selectedRule || isSimulating}
        >
          {isSimulating ? "Simulating…" : "Simulate"}
        </button>
        <button
          onClick={handleTrigger}
          className="br-btn border px-4 py-2 text-xs font-semibold uppercase tracking-wider transition bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-40 dark:bg-emerald-700 dark:hover:bg-emerald-600"
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
        <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>
          Loading logs…
        </p>
      ) : logs.length === 0 ? (
        <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>
          No executions yet.
        </p>
      ) : (
        logs.map((log) => (
          <div key={log.exec_id} className="cep-builder-log-entry p-3 text-xs">
            <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
              <span>{new Date(log.triggered_at).toLocaleString("ko-KR")}</span>
              <span
                className={cn(
                  "br-badge border px-2 py-0.5 uppercase tracking-wider",
                  log.status === "success" && "border-emerald-400 text-emerald-300",
                  log.status === "dry_run" && "bg-transparent text-slate-400 dark:text-slate-500",
                  log.status !== "success" &&
                    log.status !== "dry_run" &&
                    "border-rose-500 text-rose-300",
                )}
              >
                {log.status}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Duration {log.duration_ms} ms
            </p>
            {log.error_message ? (
              <p className="mt-1 text-tiny text-rose-400">Error: {log.error_message}</p>
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
            className={cn(
              "br-badge border px-3 py-1 text-tiny uppercase tracking-wider transition",
              activeTab === tab.id ? "bg-sky-500/10 border-sky-400 text-sky-400" : "bg-transparent",
            )}
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
        <div className="cep-builder-status-box p-3 text-xs">
          <p className="cep-builder-label">Metadata</p>
          {selectedRule ? (
            <div className="mt-2 space-y-1 text-xs text-slate-500 dark:text-slate-400">
              <p>Trigger type: {selectedRule.trigger_type}</p>
              <p>Last updated: {new Date(selectedRule.updated_at).toLocaleString("ko-KR")}</p>
            </div>
          ) : (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Select a rule to see its metadata.
            </p>
          )}
        </div>
      ) : activeTab === "test" ? (
        <div className="space-y-3">
          {draftTestOk === true && simulateResult && (
            <div className="br-section border-emerald-500/50 bg-emerald-500/10 p-4 text-xs">
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-wider text-emerald-400 font-semibold">
                  Draft Simulation Result
                </p>
                <span className="text-tiny br-badge border border-emerald-400 bg-emerald-400/20 px-2 py-0.5 uppercase tracking-wider text-emerald-300">
                  Pass
                </span>
              </div>
              <pre className="mt-2 max-h-60 overflow-auto br-section p-3 text-xs custom-scrollbar code-block">
                {JSON.stringify(simulateResult, null, 2)}
              </pre>
            </div>
          )}
          <div className="cep-builder-status-box p-4 text-xs">
            <p className="cep-builder-label">Simulation result</p>
            <pre className="mt-2 max-h-40 overflow-auto br-card p-3 text-xs code-block">
              {simulateResult
                ? JSON.stringify(simulateResult, null, 2)
                : "Run a simulation to inspect payload."}
            </pre>
          </div>
          <div className="cep-builder-status-box p-4 text-xs">
            <p className="cep-builder-label">Manual trigger result</p>
            <pre className="mt-2 max-h-40 overflow-auto br-card p-3 text-xs code-block">
              {triggerResult
                ? JSON.stringify(triggerResult, null, 2)
                : "Trigger once to record an execution log."}
            </pre>
          </div>
        </div>
      ) : (
        <div className="cep-builder-status-box p-4 text-xs">
          <p className="cep-builder-label">Logs</p>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            Click reload to refresh logs or trigger a rule to write entries.
          </p>
        </div>
      )}
    </div>
  );

  const leftPane = (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="left-panel-title">CEP rules</p>
        <button
          onClick={handleNew}
          className="text-tiny uppercase tracking-wider underline text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
        >
          New
        </button>
      </div>
      <input
        value={searchTerm}
        onChange={(event) => setSearchTerm(event.target.value)}
        placeholder="Search rules"
        className="w-full cep-builder-input"
      />
      <div className="space-y-2">
        {filteredRules.length === 0 ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">No rules found.</p>
        ) : (
          filteredRules.map((rule) => (
            <button
              key={rule.rule_id}
              onClick={() => {
                setSelectedId(rule.rule_id);
                setActiveTab("definition");
              }}
              className={cn(
                "cep-builder-rule-item",
                selectedId === rule.rule_id && "cep-builder-rule-item-selected",
              )}
            >
              <p>{rule.rule_name}</p>
              <p>{rule.trigger_type}</p>
            </button>
          ))
        )}
      </div>
    </div>
  );

  const processAssistantDraft = useCallback(
    (messageText: string, isComplete: boolean) => {
      setLastAssistantRaw(messageText);
      const result = parseCepDraft(messageText);
      const parseError = "error" in result ? result.error : null;
      setLastParseStatus(result.ok ? "success" : "fail");
      setLastParseError(parseError);
      if (result.ok && result.draft) {
        if (isComplete) {
          recordCopilotMetric("cep-builder", "parse_success");
          const snapshotId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
          setDraftHistory((prev) =>
            [
              {
                id: snapshotId,
                createdAt: new Date().toISOString(),
                draft: result.draft as CepDraft,
              },
              ...prev,
            ].slice(0, 8),
          );
        }
        setDraftApi(result.draft);
        setDraftStatus("draft_ready");
        setDraftNotes((prev) => prev ?? "CEP 드래프트가 준비되었습니다.");
        setDraftErrors([]);
        setDraftWarnings([]);
        setDraftTestOk(null);
        setDraftPreviewJson(JSON.stringify(result.draft, null, 2));
        setDraftPreviewSummary(result.draft.rule_name);
      } else {
        if (isComplete) {
          recordCopilotMetric("cep-builder", "parse_failure", parseError);
          setDraftApi(null);
          setDraftPreviewJson(null);
          setDraftPreviewSummary(null);
          setDraftStatus("error");
          setDraftNotes(parseError ?? "CEP 드래프트를 해석할 수 없습니다.");
          setDraftTestOk(false);
        } else if (draftStatus !== "draft_ready") {
          setDraftStatus("idle");
          setDraftNotes("AI가 답변을 생성 중입니다...");
        }
      }
    },
    [draftStatus],
  );

  const handleAssistantMessage = useCallback(
    (messageText: string) => {
      processAssistantDraft(messageText, false);
    },
    [processAssistantDraft],
  );

  const handleAssistantMessageComplete = useCallback(
    (messageText: string) => {
      processAssistantDraft(messageText, true);
    },
    [processAssistantDraft],
  );

  const selectedCompareDraft = useMemo(
    () => draftHistory.find((item) => item.id === selectedCompareDraftId) ?? null,
    [draftHistory, selectedCompareDraftId],
  );

  const compareDiffSummary = useMemo(() => {
    if (!draftApi || !selectedCompareDraft) {
      return null;
    }
    return computeCepDraftDiff(draftApi, selectedCompareDraft.draft);
  }, [draftApi, selectedCompareDraft]);

  const copilotBuilderContext = useMemo(
    () => ({
      selected_rule: selectedRule
        ? {
            rule_id: selectedRule.rule_id,
            rule_name: selectedRule.rule_name,
            trigger_type: selectedRule.trigger_type,
          }
        : null,
      draft_status: draftStatus,
      active_tab: activeTab,
      current_form: {
        rule_name: ruleName,
        trigger_type: triggerType,
      },
    }),
    [activeTab, draftStatus, ruleName, selectedRule, triggerType],
  );

  const rightPane = (
    <div className="flex flex-col h-full space-y-4 overflow-y-auto pr-1">
      <BuilderCopilotPanel
        builderSlug="cep-builder"
        instructionPrompt={COPILOT_INSTRUCTION}
        expectedContract="cep_draft"
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
          setDraftPreviewJson(null);
          setDraftPreviewSummary(null);
          setDraftDiff(null);
          setSelectedCompareDraftId(null);
        }}
        inputPlaceholder="CEP 룰 드래프트를 설명해 주세요..."
      />
      <div className="space-y-3 rounded-3xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-50">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-wider text-slate-600 dark:text-slate-400">
            Draft status
          </span>
          <span className="text-sm font-semibold text-slate-900 dark:text-slate-50">
            {draftStatusLabels[draftStatus] ?? draftStatus}
          </span>
        </div>
        {draftNotes ? (
          <p className="text-sm text-slate-600 dark:text-slate-400">{draftNotes}</p>
        ) : null}
        {draftDiff && (
          <div className="space-y-1 rounded-2xl border border-slate-200 bg-slate-100 px-3 py-2 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100">
            <p className="text-tiny uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Auto Diff
            </p>
            {draftDiff.map((item) => (
              <p key={item}>{item}</p>
            ))}
          </div>
        )}
        {draftStatus === "outdated" ? (
          <div className="rounded-2xl border border-amber-500/60 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            Draft is outdated. Apply again or regenerate.
          </div>
        ) : null}
        <div className="sticky bottom-0 w-full bg-slate-50/95 pt-3 backdrop-blur-sm dark:bg-slate-900/95">
          <div className="grid gap-2 sm:grid-cols-2">
            <button
              onClick={handlePreviewDraft}
              className="br-card border border-slate-300 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-900 transition hover:border-sky-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            >
              Preview
            </button>
            <button
              onClick={handleTestDraftWithSimulation}
              className="br-card border border-slate-300 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-900 transition hover:border-emerald-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            >
              Test (Simulate)
            </button>
            <button
              onClick={handleApplyDraft}
              className="br-card border border-slate-300 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-900 transition hover:border-indigo-400 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              disabled={!draftApi || draftTestOk !== true}
            >
              Apply
            </button>
            <button
              onClick={handleSaveDraft}
              className="br-card border border-emerald-500/50 bg-emerald-500/70 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-white transition hover:bg-emerald-500 disabled:opacity-50"
              disabled={!draftApi || draftTestOk !== true}
            >
              Save
            </button>
          </div>
        </div>
        {!draftApi && (
          <p className="text-xs text-slate-600 dark:text-slate-400">
            No draft yet. Ask the copilot to generate one.
            {lastParseError ? ` Parse error: ${lastParseError}` : ""}
          </p>
        )}
        {draftErrors.length > 0 && (
          <div className="space-y-1 br-card border border-rose-500/60 bg-rose-500/5 px-3 py-2 text-xs text-rose-200">
            {draftErrors.map((error) => (
              <p key={error}>{error}</p>
            ))}
          </div>
        )}
        {draftWarnings.length > 0 && (
          <div className="space-y-1 rounded-2xl border border-amber-500/60 bg-amber-500/5 px-3 py-2 text-xs text-amber-200">
            {draftWarnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        )}
        {draftPreviewSummary && draftPreviewJson ? (
          <div className="space-y-2 rounded-2xl border border-slate-200 bg-slate-100 p-3 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100">
            <p className="text-xs uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Preview
            </p>
            <p className="text-sm text-slate-900 dark:text-slate-50">{draftPreviewSummary}</p>
            <pre className="max-h-48 overflow-auto rounded-xl bg-white p-2 text-xs text-slate-600 dark:bg-slate-950 dark:text-slate-300">
              {draftPreviewJson}
            </pre>
          </div>
        ) : null}
        <div className="space-y-2 rounded-2xl border border-slate-200 bg-slate-100 p-3 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100">
          <p className="text-xs uppercase tracking-wider text-slate-600 dark:text-slate-400">
            Multi Draft Compare
          </p>
          <select
            value={selectedCompareDraftId ?? ""}
            onChange={(event) => setSelectedCompareDraftId(event.target.value || null)}
            className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
          >
            <option value="">비교할 드래프트 선택</option>
            {draftHistory.map((item) => (
              <option key={item.id} value={item.id}>
                {new Date(item.createdAt).toLocaleTimeString("ko-KR")} · {item.draft.rule_name}
              </option>
            ))}
          </select>
          {compareDiffSummary && (
            <div className="space-y-1">
              {compareDiffSummary.map((line) => (
                <p key={line}>{line}</p>
              ))}
            </div>
          )}
        </div>
        <div className="space-y-2 rounded-2xl border border-slate-200 bg-slate-100 p-3 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100">
          <p className="text-xs uppercase tracking-wider text-slate-600 dark:text-slate-400">
            Example Prompts
          </p>
          <div className="max-h-40 space-y-1 overflow-auto">
            {CEP_COPILOT_EXAMPLE_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => navigator.clipboard.writeText(prompt)}
                className="w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-left text-xs text-slate-600 transition hover:border-sky-600 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300"
                title="클릭하면 프롬프트가 클립보드에 복사됩니다."
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
        <details className="rounded-2xl border border-slate-200 bg-slate-100 p-3 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100">
          <summary className="cursor-pointer text-xs uppercase tracking-wider text-slate-600 dark:text-slate-400">
            Debug
          </summary>
          <div className="mt-2 space-y-1">
            <p className="text-tiny uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Save target: {saveTarget ?? "none"}
            </p>
            {lastSaveError ? (
              <p className="text-xs text-rose-300">Save error: {lastSaveError}</p>
            ) : null}
            <p className="text-tiny uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Selected rule
            </p>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              {selectedRule ? `${selectedRule.rule_name} (${selectedRule.rule_id})` : "새 룰"}
            </p>
            <p className="text-tiny uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Parse status: {lastParseStatus}
            </p>
            {lastParseError ? (
              <p className="text-xs text-rose-300">Error: {lastParseError}</p>
            ) : null}
            <p className="text-tiny uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Last assistant raw
            </p>
            <pre className="max-h-32 overflow-auto rounded-xl bg-white p-2 text-tiny text-slate-900 dark:bg-slate-950 dark:text-slate-100">
              {lastAssistantRaw || "없음"}
            </pre>
            {draftApi ? (
              <>
                <p className="text-tiny uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Draft JSON
                </p>
                <pre className="max-h-32 overflow-auto rounded-xl bg-white p-2 text-tiny text-slate-900 dark:bg-slate-950 dark:text-slate-100">
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
    <div className="page-cep-builder min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-50">
      <PageHeader
        title="Event Rule Maker"
        description="런타임 API와 연동되는 CEP 이벤트 규칙을 정의하고, 시뮬레이션하며, 트리거합니다."
      />
      <main className="min-h-[calc(100vh-96px)] py-6">
        <BuilderShell
          leftPane={leftPane}
          centerTop={centerTop}
          centerBottom={centerBottom}
          rightPane={rightPane}
        />
      </main>
    </div>
  );
}
