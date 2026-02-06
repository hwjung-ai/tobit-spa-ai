"use client";

import { useState } from "react";
import { FormFieldGroup } from "./FormFieldGroup";

interface SimulationResult {
  matched: boolean;
  conditionResults: Record<string, boolean>;
  triggeredActions: string[];
  explanation: string;
}

interface SimulationPanelProps {
  isLoading?: boolean;
  onSimulate: (testPayload: Record<string, any>) => Promise<SimulationResult>;
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
    <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">규칙 시뮬레이션</h3>
        <span className="text-xs text-slate-500">저장 전 테스트</span>
      </div>

      <FormFieldGroup label="테스트 데이터 (JSON)" required={true}>
        <textarea
          value={testPayload}
          onChange={(e) => setTestPayload(e.target.value)}
          rows={6}
          className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 font-mono text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
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
            className={`rounded-lg border p-3 ${
              result.matched
                ? "border-emerald-500/50 bg-emerald-500/10"
                : "border-slate-700 bg-slate-900/20"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-lg">
                {result.matched ? "✅" : "⚪"}
              </span>
              <div>
                <p className="text-xs font-semibold text-white">
                  {result.matched ? "조건 일치됨" : "조건 일치 안 됨"}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  {result.explanation}
                </p>
              </div>
            </div>
          </div>

          {Object.keys(result.conditionResults).length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-300">조건 결과:</p>
              {Object.entries(result.conditionResults).map(([name, value]) => (
                <div
                  key={name}
                  className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/40 p-2 text-xs"
                >
                  <span className="text-sm">
                    {value ? "✓" : "✗"}
                  </span>
                  <span className="text-slate-300">{name}</span>
                  <span className={value ? "text-emerald-400" : "text-slate-500"}>
                    {value ? "일치" : "불일치"}
                  </span>
                </div>
              ))}
            </div>
          )}

          {result.triggeredActions.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-300">실행될 액션:</p>
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
