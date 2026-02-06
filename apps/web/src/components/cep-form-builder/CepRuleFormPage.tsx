"use client";

import { useState, useCallback } from "react";
import { BasicInfoSection } from "./BasicInfoSection";
import { TriggerSection } from "./TriggerSection";
import { ConditionsSection } from "./ConditionsSection";
import { WindowingSection } from "./WindowingSection";
import { AggregationSection } from "./AggregationSection";
import { EnrichmentSection } from "./EnrichmentSection";
import { ActionsSection } from "./ActionsSection";
import { SimulationPanel } from "./SimulationPanel";
import { JsonPreview } from "./JsonPreview";

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

interface Aggregation {
  id: string;
  type: "avg" | "sum" | "min" | "max" | "count" | "stddev";
  field?: string;
  outputAlias?: string;
}

interface Enrichment {
  id: string;
  type: "lookup" | "aggregate" | "ml_model";
  source?: string;
  key?: string;
  outputField?: string;
}

interface CepRuleFormData {
  ruleName: string;
  description: string;
  isActive: boolean;
  triggerType: "metric" | "event" | "schedule";
  triggerSpec: Record<string, any>;
  conditions: Condition[];
  conditionLogic: "AND" | "OR" | "NOT";
  windowConfig: Record<string, any>;
  aggregations: Aggregation[];
  groupByFields: string[];
  enrichments: Enrichment[];
  actions: Action[];
}

interface CepRuleFormPageProps {
  onSave?: (data: CepRuleFormData) => Promise<void>;
  onCancel?: () => void;
  initialData?: Partial<CepRuleFormData>;
  isLoading?: boolean;
}

export function CepRuleFormPage({
  onSave,
  onCancel,
  initialData,
  isLoading = false,
}: CepRuleFormPageProps) {
  const [formData, setFormData] = useState<CepRuleFormData>({
    ruleName: "",
    description: "",
    isActive: true,
    triggerType: "metric",
    triggerSpec: {},
    conditions: [],
    conditionLogic: "AND",
    windowConfig: {},
    aggregations: [],
    groupByFields: [],
    enrichments: [],
    actions: [],
    ...initialData,
  });

  const [showJsonPreview, setShowJsonPreview] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const isFormValid = useCallback(() => {
    return (
      formData.ruleName.length > 0 &&
      Object.keys(formData.triggerSpec).length > 0 &&
      formData.actions.length > 0
    );
  }, [formData]);

  const handleSave = async () => {
    if (!isFormValid()) {
      setSaveError("필수 항목을 모두 입력해주세요");
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      if (onSave) {
        await onSave(formData);
      }
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "저장 실패";
      setSaveError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const buildJsonPreview = useCallback(() => {
    return {
      rule_name: formData.ruleName,
      description: formData.description,
      is_active: formData.isActive,
      trigger_type: formData.triggerType,
      trigger_spec: formData.triggerSpec,
      ...(formData.conditions.length > 0 && {
        composite_condition: {
          conditions: formData.conditions.map((c) => ({
            field: c.field,
            op: c.op,
            value: c.value,
          })),
          logic: formData.conditionLogic,
        },
      }),
      ...(Object.keys(formData.windowConfig).length > 0 && {
        window_config: formData.windowConfig,
      }),
      ...(formData.aggregations.length > 0 && {
        aggregations: formData.aggregations.map((a) => ({
          type: a.type,
          field: a.field,
          output_alias: a.outputAlias,
        })),
        group_by_fields: formData.groupByFields,
      }),
      ...(formData.enrichments.length > 0 && {
        enrichments: formData.enrichments.map((e) => ({
          type: e.type,
          source: e.source,
          key: e.key,
          output_field: e.outputField,
        })),
      }),
      actions: formData.actions.map((a) => ({
        type: a.type,
        endpoint: a.endpoint,
        method: a.method,
        channels: a.channels,
        message: a.message,
      })),
    };
  }, [formData]);

  const handleSimulate = useCallback(
    async (testPayload: Record<string, any>) => {
      // 실제 API 호출로 대체 필요
      // POST /api/cep/rules/preview
      const response = await fetch("/api/cep/rules/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trigger_spec: formData.triggerSpec,
          conditions: formData.conditions,
          condition_logic: formData.conditionLogic,
          test_payload: testPayload,
        }),
      });

      if (!response.ok) {
        throw new Error("시뮬레이션 API 호출 실패");
      }

      return response.json();
    },
    [formData]
  );

  return (
    <div className="max-w-4xl mx-auto space-y-6 py-6">
      {/* 헤더 */}
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-white">CEP 규칙 빌더</h1>
        <p className="text-sm text-slate-400">
          폼 기반으로 복합 이벤트 처리 규칙을 만들어보세요
        </p>
      </div>

      {/* 에러/성공 메시지 */}
      {saveError && (
        <div className="rounded-lg border border-rose-500/50 bg-rose-500/10 p-4">
          <p className="text-sm text-rose-400">❌ {saveError}</p>
        </div>
      )}

      {saveSuccess && (
        <div className="rounded-lg border border-emerald-500/50 bg-emerald-500/10 p-4">
          <p className="text-sm text-emerald-400">✅ 규칙이 저장되었습니다</p>
        </div>
      )}

      {/* 기본 정보 */}
      <BasicInfoSection
        ruleName={formData.ruleName}
        description={formData.description}
        isActive={formData.isActive}
        onRuleNameChange={(name) =>
          setFormData({ ...formData, ruleName: name })
        }
        onDescriptionChange={(desc) =>
          setFormData({ ...formData, description: desc })
        }
        onActiveChange={(active) =>
          setFormData({ ...formData, isActive: active })
        }
      />

      {/* 트리거 */}
      <TriggerSection
        triggerType={formData.triggerType}
        triggerSpec={formData.triggerSpec}
        onTriggerTypeChange={(type) => {
          setFormData({
            ...formData,
            triggerType: type,
            triggerSpec: {}, // 트리거 타입 변경 시 초기화
          });
        }}
        onTriggerSpecChange={(spec) =>
          setFormData({ ...formData, triggerSpec: spec })
        }
      />

      {/* 복합 조건 */}
      <ConditionsSection
        conditions={formData.conditions}
        logic={formData.conditionLogic}
        onConditionsChange={(conds) =>
          setFormData({ ...formData, conditions: conds })
        }
        onLogicChange={(logic) =>
          setFormData({ ...formData, conditionLogic: logic })
        }
      />

      {/* 윈도우 */}
      <WindowingSection
        windowConfig={formData.windowConfig}
        onWindowConfigChange={(config) =>
          setFormData({ ...formData, windowConfig: config })
        }
      />

      {/* 집계 */}
      <AggregationSection
        aggregations={formData.aggregations}
        groupByFields={formData.groupByFields}
        onAggregationsChange={(aggs) =>
          setFormData({ ...formData, aggregations: aggs })
        }
        onGroupByChange={(fields) =>
          setFormData({ ...formData, groupByFields: fields })
        }
      />

      {/* 데이터 보강 */}
      <EnrichmentSection
        enrichments={formData.enrichments}
        onEnrichmentsChange={(enr) =>
          setFormData({ ...formData, enrichments: enr })
        }
      />

      {/* 액션 */}
      <ActionsSection
        actions={formData.actions}
        onActionsChange={(acts) =>
          setFormData({ ...formData, actions: acts })
        }
      />

      {/* 시뮬레이션 */}
      <SimulationPanel
        isLoading={isLoading}
        onSimulate={handleSimulate}
      />

      {/* JSON 미리보기 */}
      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
        <div
          className="flex items-center justify-between cursor-pointer hover:bg-slate-900/40 p-2 rounded-lg"
          onClick={() => setShowJsonPreview(!showJsonPreview)}
        >
          <h3 className="text-sm font-semibold text-white">JSON 미리보기</h3>
          <span className="text-sm text-slate-400">
            {showJsonPreview ? "▼" : "▶"}
          </span>
        </div>
        {showJsonPreview && (
          <div className="mt-3">
            <JsonPreview data={buildJsonPreview()} />
          </div>
        )}
      </div>

      {/* 버튼 */}
      <div className="flex gap-3 sticky bottom-0 bg-slate-950/80 p-4 rounded-lg backdrop-blur">
        <button
          onClick={onCancel}
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-900/80"
        >
          취소
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving || isLoading || !isFormValid()}
          className="flex-1 rounded-lg border border-emerald-500/50 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving || isLoading ? "저장 중..." : "✓ 규칙 저장"}
        </button>
      </div>
    </div>
  );
}
