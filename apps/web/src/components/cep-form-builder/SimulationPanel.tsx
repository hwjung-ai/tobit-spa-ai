"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { FormFieldGroup } from "./FormFieldGroup";

interface SimulationResult {
  matched: boolean;
  conditionResults: Record<string, boolean>;
  triggeredActions: string[];
  explanation: string;
}

interface SimulationPanelProps {
  isLoading?: boolean;
  onSimulate: (testPayload: Record<string, unknown>) => Promise<SimulationResult>;
}

export function SimulationPanel({
  isLoading = false,
  onSimulate,
}: SimulationPanelProps) {
  const [testPayload, setTestPayload] = useState(
    JSON.stringify(
      {
        cpu_usage: 75,
        memory_percent: 65,
        status: "running",
      },
      null,
      2
    )
  );
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSimulate = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const payload = JSON.parse(testPayload);
      const simulationResult = await onSimulate(payload);
      setResult(simulationResult);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "시뮬레이션 실패";
      setError(errorMessage);
      setResult(null);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="cep-section-container">
      <div className="cep-section-header">
        <h3 className="cep-section-title">규칙 시뮬레이션</h3>
        <span className="cep-section-counter">저장 전 테스트</span>
      </div>

      <FormFieldGroup label="테스트 데이터 (JSON)" required={true}>
        <textarea
          value={testPayload}
          onChange={(e) => setTestPayload(e.target.value)}
          rows={6}
          className="cep-input-full-lg font-mono"
          placeholder='{"cpu_usage": 85, "memory_percent": 75}'
        />
      </FormFieldGroup>

      {error && (
        <div className="rounded-lg border border-rose-500/50 bg-rose-500/10 p-3">
          <p className="text-xs text-rose-400">❌ {error}</p>
        </div>
      )}

      <button
        onClick={handleSimulate}
        disabled={isRunning || isLoading}
        className="w-full rounded-lg border border-sky-500/50 bg-sky-500/10 px-3 py-2 text-xs font-semibold text-sky-400 hover:bg-sky-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isRunning || isLoading ? "실행 중..." : "🧪 시뮬레이션 실행"}
      </button>

      {result && (
        <div className="space-y-3">
           <div
             className={cn(
               "rounded-lg border p-3",
               result.matched && "border-emerald-500/50 bg-emerald-500/10"
             )}
           >
            <div className="flex items-center gap-2">
              <span className="text-lg">
                {result.matched ? "✅" : "⚪"}
              </span>
              <div>
                <p className="cep-condition-label">
                  {result.matched ? "조건 일치됨" : "조건 일치 안 됨"}
                </p>
                <p className="cep-text-muted mt-1">
                  {result.explanation}
                </p>
              </div>
            </div>
          </div>

          {Object.keys(result.conditionResults).length > 0 && (
            <div className="space-y-2">
              <p className="cep-text-muted-sm font-semibold">조건 결과:</p>
              {Object.entries(result.conditionResults).map(([name, value]) => (
                <div
                  key={name}
                  className="cep-condition-group flex items-center gap-2"
                >
                  <span className="text-sm">
                    {value ? "✓" : "✗"}
                  </span>
                  <span className="cep-text-muted">{name}</span>
                  <span className={value ? "text-emerald-400" : "cep-text-muted"}>
                    {value ? "일치" : "불일치"}
                  </span>
                </div>
              ))}
            </div>
          )}

          {result.triggeredActions.length > 0 && (
            <div className="space-y-2">
              <p className="cep-text-muted-sm font-semibold">실행될 액션:</p>
              {result.triggeredActions.map((action, index) => (
                <div
                  key={index}
                  className="rounded-lg border border-emerald-500/50 bg-emerald-500/10 p-2 text-xs text-emerald-400"
                >
                  📤 {action}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
