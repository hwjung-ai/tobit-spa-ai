"use client";

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
    <div className="cep-section-container">
      <div className="cep-section-header">
        <h3 className="cep-section-title">조건 설정 (선택사항)</h3>
        <div className="flex items-center gap-2">
          <select
            value={logic}
            onChange={(e) => onLogicChange(e.target.value as "AND" | "OR" | "NOT")}
            className="cep-select"
          >
            <option value="AND">AND</option>
            <option value="OR">OR</option>
            <option value="NOT">NOT</option>
          </select>
        </div>
      </div>

      {conditions.length > 0 && (
        <div className="space-y-3">
          {conditions.map((condition) => (
            <div
              key={condition.id}
              className="cep-condition-group flex items-end gap-2"
            >
              <div className="flex-1 space-y-1">
                <label className="cep-window-label">필드</label>
                <input
                  type="text"
                  value={condition.field}
                  onChange={(e) =>
                    updateCondition(condition.id, { field: e.target.value })
                  }
                  placeholder="예: cpu_usage"
                  className="cep-input-full"
                />
              </div>
              <div className="w-20 space-y-1">
                <label className="cep-window-label">연산자</label>
                <select
                  value={condition.op}
                  onChange={(e) =>
                    updateCondition(condition.id, { op: e.target.value })
                  }
                  className="cep-select-primary w-full"
                >
                  {OPERATORS.map((op) => (
                    <option key={op} value={op}>
                      {op}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex-1 space-y-1">
                <label className="cep-window-label">값</label>
                <input
                  type="text"
                  value={condition.value}
                  onChange={(e) =>
                    updateCondition(condition.id, { value: e.target.value })
                  }
                  placeholder="값 입력"
                  className="cep-input-full"
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
