"use client";

import { useState } from "react";
import { FormFieldGroup } from "./FormFieldGroup";

interface Condition {
  id: string;
  field: string;
  op: string;
  value: string;
}

interface ConditionsSectionProps {
  conditions: Condition[];
  logic: "AND" | "OR" | "NOT";
  onConditionsChange: (conditions: Condition[]) => void;
  onLogicChange: (logic: "AND" | "OR" | "NOT") => void;
  onAiGenerate?: () => void;
}

const OPERATORS = [">", "<", ">=", "<=", "==", "!=", "in", "contains"];

export function ConditionsSection({
  conditions,
  logic,
  onConditionsChange,
  onLogicChange,
  onAiGenerate,
}: ConditionsSectionProps) {
  const addCondition = () => {
    const newCondition = {
      id: `cond-${Date.now()}`,
      field: "",
      op: "==",
      value: "",
    };
    onConditionsChange([...conditions, newCondition]);
  };

  const removeCondition = (id: string) => {
    onConditionsChange(conditions.filter((c) => c.id !== id));
  };

  const updateCondition = (id: string, updates: Partial<Condition>) => {
    onConditionsChange(
      conditions.map((c) => (c.id === id ? { ...c, ...updates } : c))
    );
  };

  return (
    <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">조건 설정 (선택사항)</h3>
        <div className="flex items-center gap-2">
          <select
            value={logic}
            onChange={(e) => onLogicChange(e.target.value as any)}
            className="rounded-lg border border-slate-700 bg-slate-900/60 px-2 py-1 text-xs text-white"
          >
            <option value="AND">AND</option>
            <option value="OR">OR</option>
            <option value="NOT">NOT</option>
          </select>
        </div>
      </div>

      {conditions.length > 0 && (
        <div className="space-y-3">
          {conditions.map((condition, index) => (
            <div
              key={condition.id}
              className="flex items-end gap-2 rounded-lg border border-slate-700 bg-slate-900/40 p-3"
            >
              <div className="flex-1 space-y-1">
                <label className="text-xs text-slate-400">필드</label>
                <input
                  type="text"
                  value={condition.field}
                  onChange={(e) =>
                    updateCondition(condition.id, { field: e.target.value })
                  }
                  placeholder="예: cpu_usage"
                  className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-2 py-1 text-xs text-white placeholder-slate-500"
                />
              </div>
              <div className="w-20 space-y-1">
                <label className="text-xs text-slate-400">연산자</label>
                <select
                  value={condition.op}
                  onChange={(e) =>
                    updateCondition(condition.id, { op: e.target.value })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-2 py-1 text-xs text-white"
                >
                  {OPERATORS.map((op) => (
                    <option key={op} value={op}>
                      {op}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex-1 space-y-1">
                <label className="text-xs text-slate-400">값</label>
                <input
                  type="text"
                  value={condition.value}
                  onChange={(e) =>
                    updateCondition(condition.id, { value: e.target.value })
                  }
                  placeholder="값 입력"
                  className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-2 py-1 text-xs text-white placeholder-slate-500"
                />
              </div>
              <button
                onClick={() => removeCondition(condition.id)}
                className="rounded-lg border border-rose-500/50 bg-rose-500/10 px-2 py-1 text-xs text-rose-400 hover:bg-rose-500/20"
              >
                삭제
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={addCondition}
          className="flex-1 rounded-lg border border-sky-500/50 bg-sky-500/10 px-3 py-2 text-xs font-semibold text-sky-400 hover:bg-sky-500/20"
        >
          + 조건 추가
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
