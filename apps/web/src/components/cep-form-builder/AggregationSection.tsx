"use client";

import { useState } from "react";

interface Aggregation {
  id: string;
  type: "count" | "sum" | "avg" | "min" | "max" | "std" | "percentile";
  fieldName?: string;
  outputName?: string;
  percentile?: number;
}

interface AggregationSectionProps {
  aggregations: Aggregation[];
  onAggregationsChange: (aggregations: Aggregation[]) => void;
  onAiGenerate?: () => void;
}

const AGG_TYPES = [
  { value: "count", label: "Count" },
  { value: "sum", label: "Sum" },
  { value: "avg", label: "Average" },
  { value: "min", label: "Min" },
  { value: "max", label: "Max" },
  { value: "std", label: "Std Dev" },
  { value: "percentile", label: "Percentile" },
];

export function AggregationSection({
  aggregations,
  onAggregationsChange,
  onAiGenerate,
}: AggregationSectionProps) {
  const [fieldInput, setFieldInput] = useState("");

  const addAggregation = () => {
    const newAggregation: Aggregation = {
      id: `agg-${Date.now()}`,
      type: "count",
    };
    onAggregationsChange([...aggregations, newAggregation]);
  };

  const removeAggregation = (id: string) => {
    onAggregationsChange(aggregations.filter((a) => a.id !== id));
  };

  const updateAggregation = (id: string, updates: Partial<Aggregation>) => {
    onAggregationsChange(aggregations.map((a) => (a.id === id ? { ...a, ...updates } : a)));
  };

  return (
    <div className="cep-section-container">
      <div className="cep-section-header">
        <h3 className="cep-section-title">집계 설정 (선택사항)</h3>
        <span className="cep-section-counter">{aggregations.length}개</span>
      </div>

      <div className="space-y-3">
        <input
          type="text"
          value={fieldInput}
          onChange={(e) => setFieldInput(e.target.value)}
          placeholder="필드명 입력"
          className="cep-input-full-lg"
        />
        {aggregations.length === 0 ? (
          <div className="cep-empty-state">
            <p className="cep-empty-state-text">집계 함수를 추가해주세요</p>
          </div>
        ) : (
          <div className="space-y-3">
            {aggregations.map((agg) => (
              <div
                key={agg.id}
                className="cep-item-card"
              >
                <div className="cep-window-setting">
                  <label className="cep-window-label">집계 타입</label>
                  <select
                    value={agg.type}
                    onChange={(e) =>
                      updateAggregation(agg.id, {
                        type: e.target.value as "count" | "sum" | "avg" | "min" | "max" | "std" | "percentile",
                      })
                    }
                    className="cep-select cep-input-full mt-1"
                  >
                    {AGG_TYPES.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                {agg.type !== "count" && (
                  <div className="cep-window-setting">
                    <label className="cep-window-label">필드명</label>
                    <input
                      type="text"
                      value={agg.fieldName || ""}
                      onChange={(e) =>
                        updateAggregation(agg.id, { fieldName: e.target.value })
                      }
                      placeholder="대상 필드명"
                      className="cep-input-full-lg mt-1"
                    />
                  </div>
                )}

                <div className="cep-window-setting">
                  <label className="cep-window-label">출력명</label>
                  <input
                    type="text"
                    value={agg.outputName || ""}
                    onChange={(e) =>
                      updateAggregation(agg.id, { outputName: e.target.value })
                    }
                    placeholder="결과 필드명"
                    className="cep-select-primary cep-input-full-lg mt-1"
                  />
                </div>

                {agg.type === "percentile" && (
                  <div className="cep-window-setting">
                    <label className="cep-window-label">백분위</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={agg.percentile || 50}
                      onChange={(e) =>
                        updateAggregation(agg.id, {
                          percentile: parseFloat(e.target.value),
                        })
                      }
                      placeholder="0-100"
                      className="cep-input-full mt-1"
                    />
                  </div>
                )}

                <button
                  onClick={() => removeAggregation(agg.id)}
                  className="w-full rounded-lg border border-rose-500/50 bg-rose-500/10 px-2 py-1 text-xs text-rose-400 hover:bg-rose-500/20"
                >
                  삭제
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <button
          onClick={addAggregation}
          className="flex-1 rounded-lg border border-emerald-500/50 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20"
        >
          + 집계 추가
        </button>
        {onAiGenerate && (
          <button
            onClick={onAiGenerate}
            className="flex-1 rounded-lg border border-purple-500/50 bg-purple-500/10 px-3 py-2 text-xs font-semibold text-purple-400 hover:bg-purple-500/20"
          >
            🤖 AI 생성
          </button>
        )}
      </div>
    </div>
  );
}
