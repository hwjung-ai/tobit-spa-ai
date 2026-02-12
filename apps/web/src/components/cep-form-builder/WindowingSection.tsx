"use client";

import { FormFieldGroup } from "./FormFieldGroup";

type WindowType = "tumbling" | "sliding" | "session";

interface WindowConfig {
  type?: WindowType;
  size?: string;
  slide?: string;
  timeout?: string;
}

interface WindowingSectionProps {
  windowConfig: WindowConfig;
  onWindowConfigChange: (config: WindowConfig) => void;
}

const WINDOW_TYPES = [
  {
    value: "tumbling" as const,
    label: "Tumbling Window",
    description: "고정 크기의 겹치지 않는 시간 윈도우",
  },
  {
    value: "sliding" as const,
    label: "Sliding Window",
    description: "겹치는 시간 윈도우 (Slide 간격)",
  },
  {
    value: "session" as const,
    label: "Session Window",
    description: "사용자 세션 기반 윈도우",
  },
];

const TIME_UNITS = ["1s", "10s", "30s", "1m", "5m", "10m", "30m", "1h"];

export function WindowingSection({
  windowConfig,
  onWindowConfigChange,
}: WindowingSectionProps) {
  const handleWindowTypeChange = (type: WindowType) => {
    onWindowConfigChange({
      ...windowConfig,
      type,
      // 기본값 설정
      size: windowConfig.size || "5m",
      slide:
        type === "sliding" ? windowConfig.slide || "1m" : windowConfig.slide,
      timeout:
        type === "session" ? windowConfig.timeout || "10m" : windowConfig.timeout,
    });
  };

  return (
    <div className="space-y-4 rounded-2xl p-4" style={{ border: "1px solid var(--border)", backgroundColor: "var(--surface-overlay)" }}>
      <h3 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>윈도우 설정 (선택사항)</h3>
      <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
        데이터를 시간 단위로 분할하여 집계합니다
      </p>

      <FormFieldGroup label="윈도우 타입">
        <div className="space-y-2">
          {WINDOW_TYPES.map((wt) => (
            <label
              key={wt.value}
              className="flex items-start gap-3 rounded-lg p-3 cursor-pointer" style={{ border: "1px solid var(--border-muted)", backgroundColor: "rgba(30, 41, 59, 0.4)" }}
            >
              <input
                type="radio"
                name="windowType"
                value={wt.value}
                checked={windowConfig.type === wt.value}
                onChange={() => handleWindowTypeChange(wt.value)}
                className="mt-1 rounded"
              />
              <div className="flex-1">
                <div className="text-xs font-medium" style={{ color: "var(--foreground)" }}>{wt.label}</div>
                <div className="text-xs" style={{ color: "var(--muted-foreground)" }}>{wt.description}</div>
              </div>
            </label>
          ))}
        </div>
      </FormFieldGroup>

      {windowConfig.type && (
        <>
          <div className="flex gap-3">
            <FormFieldGroup label="윈도우 크기" required={true}>
              <select
                value={windowConfig.size || "5m"}
                onChange={(e) =>
                  onWindowConfigChange({
                    ...windowConfig,
                    size: e.target.value,
                  })
                }
                className="w-full rounded-lg px-3 py-2 text-xs" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
              >
                {TIME_UNITS.map((unit) => (
                  <option key={unit} value={unit}>
                    {unit}
                  </option>
                ))}
              </select>
            </FormFieldGroup>

            {windowConfig.type === "sliding" && (
              <FormFieldGroup label="Slide 간격" required={true}>
                <select
                  value={windowConfig.slide || "1m"}
                  onChange={(e) =>
                    onWindowConfigChange({
                      ...windowConfig,
                      slide: e.target.value,
                    })
                  }
                  className="w-full rounded-lg px-3 py-2 text-xs" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
                >
                  {TIME_UNITS.map((unit) => (
                    <option key={unit} value={unit}>
                      {unit}
                    </option>
                  ))}
                </select>
              </FormFieldGroup>
            )}

            {windowConfig.type === "session" && (
              <FormFieldGroup label="Session Timeout" required={true}>
                <select
                  value={windowConfig.timeout || "10m"}
                  onChange={(e) =>
                    onWindowConfigChange({
                      ...windowConfig,
                      timeout: e.target.value,
                    })
                  }
                  className="w-full rounded-lg px-3 py-2 text-xs" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
                >
                  {TIME_UNITS.map((unit) => (
                    <option key={unit} value={unit}>
                      {unit}
                    </option>
                  ))}
                </select>
              </FormFieldGroup>
            )}
          </div>

          <div className="rounded-lg p-3" style={{ border: "1px solid var(--border-muted)", backgroundColor: "rgba(30, 41, 59, 0.2)" }}>
            <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              {windowConfig.type === "tumbling" &&
                `✓ ${windowConfig.size} 크기의 윈도우로 데이터를 분할합니다`}
              {windowConfig.type === "sliding" &&
                `✓ ${windowConfig.size} 크기로 ${windowConfig.slide} 간격으로 이동하며 데이터를 처리합니다`}
              {windowConfig.type === "session" &&
                `✓ ${windowConfig.timeout} 동안 활동이 없으면 세션을 종료합니다`}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
