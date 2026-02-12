"use client";

import { FormFieldGroup } from "./FormFieldGroup";

interface Aggregation {
  id: string;
  type: "avg" | "sum" | "min" | "max" | "count" | "stddev";
  field?: string;
  outputAlias?: string;
}

interface AggregationSectionProps {
  aggregations: Aggregation[];
  groupByFields?: string[];
  onAggregationsChange: (aggregations: Aggregation[]) => void;
  onGroupByChange?: (fields: string[]) => void;
}

const AGGREGATION_TYPES = [
  { value: "avg", label: "평균" },
  { value: "sum", label: "합계" },
  { value: "min", label: "최소값" },
  { value: "max", label: "최대값" },
  { value: "count", label: "개수" },
  { value: "stddev", label: "표준편차" },
] as const;

export function AggregationSection({
  aggregations,
  groupByFields = [],
  onAggregationsChange,
  onGroupByChange,
}: AggregationSectionProps) {
  const addAggregation = () => {
    const newAggregation: Aggregation = {
      id: `agg-${Date.now()}`,
      type: "avg",
      field: "",
      outputAlias: "",
    };
    onAggregationsChange([...aggregations, newAggregation]);
  };

  const removeAggregation = (id: string) => {
    onAggregationsChange(aggregations.filter((a) => a.id !== id));
  };

  const updateAggregation = (id: string, updates: Partial<Aggregation>) => {
    onAggregationsChange(
      aggregations.map((a) => (a.id === id ? { ...a, ...updates } : a))
    );
  };

  return (
    <div className="space-y-4 rounded-2xl p-4" style={{border: "1px solid var(--border)", backgroundColor: "var(--surface-overlay)"}}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold" style={{color: "var(--foreground)"}}>집계 설정 (선택사항)</h3>
        <span className="text-xs" style={{color: "var(--muted-foreground)"}}>{aggregations.length}개</span>
      </div>

      <FormFieldGroup label="그룹화 필드" help="선택적으로 특정 필드로 데이터를 그룹화합니다">
        <input
          type="text"
          value={groupByFields.join(", ")}
          onChange={(e) =>
            onGroupByChange?.(
              e.target.value
                .split(",")
                .map((f) => f.trim())
                .filter((f) => f.length > 0)
            )
          }
          placeholder="예: region, service_name (쉼표로 구분)"
          className="w-full rounded-lg px-3 py-2 text-xs placeholder-slate-500" style={{border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)"}}
        />
      </FormFieldGroup>

      {aggregations.length === 0 ? (
        <div className="rounded-lg border border-dashed py-4 text-center" style={{borderColor: "var(--border-muted)", backgroundColor: "rgba(30, 41, 59, 0.2)"}}>
          <p className="text-xs" style={{color: "var(--muted-foreground)"}}>집계 함수를 추가해주세요</p>
        </div>
      ) : (
        <div className="space-y-3">
          {aggregations.map((agg) => (
            <div
              key={agg.id}
              className="rounded-lg p-3 space-y-2" style={{border: "1px solid var(--border-muted)", backgroundColor: "rgba(30, 41, 59, 0.4)"}}
            >
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-xs" style={{color: "var(--muted-foreground)"}}>집계 타입</label>
                  <select
                    value={agg.type}
                    onChange={(e) =>
                      updateAggregation(agg.id, {
                        type: e.target.value as any,
                      })
                    }
                    className="w-full rounded-lg px-2 py-1 text-xs mt-1" style={{border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)"}}
                  >
                    {AGGREGATION_TYPES.map((at) => (
                      <option key={at.value} value={at.value}>
                        {at.label}
                      </option>
                    ))}
                  </select>
                </div>

                {agg.type !== "count" && (
                  <div className="flex-1">
                    <label className="text-xs" style={{color: "var(--muted-foreground)"}}>필드명</label>
                    <input
                      type="text"
                      value={agg.field || ""}
                      onChange={(e) =>
                        updateAggregation(agg.id, {
                          field: e.target.value,
                        })
                      }
                      placeholder="예: cpu_usage"
                      className="w-full rounded-lg px-2 py-1 text-xs placeholder-slate-500 mt-1" style={{border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)"}}
                    />
                  </div>
                )}

                <div className="flex-1">
                  <label className="text-xs" style={{color: "var(--muted-foreground)"}}>출력명</label>
                  <input
                    type="text"
                    value={agg.outputAlias || ""}
                    onChange={(e) =>
                      updateAggregation(agg.id, {
                        outputAlias: e.target.value,
                      })
                    }
                    placeholder="예: avg_cpu"
                    className="w-full rounded-lg border   px-2 py-1 text-xs text-white placeholder-slate-500 mt-1" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}
                  />
                </div>

                <button
                  onClick={() => removeAggregation(agg.id)}
                  className="rounded-lg border border-rose-500/50 bg-rose-500/10 px-2 py-1 text-xs text-rose-400 hover:bg-rose-500/20 mt-5"
                >
                  삭제
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <button
        onClick={addAggregation}
        className="w-full rounded-lg border border-emerald-500/50 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20"
      >
        + 집계 추가
      </button>
    </div>
  );
}
