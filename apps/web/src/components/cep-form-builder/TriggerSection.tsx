"use client";

import { useState } from "react";
import { FormFieldGroup } from "./FormFieldGroup";

type TriggerType = "metric" | "event" | "schedule";

interface TriggerSpec {
  metricName?: string;
  operator?: string;
  threshold?: string;
  duration?: string;
  aggregation?: string;
  eventType?: string;
  scheduleExpression?: string;
}

interface TriggerSectionProps {
  triggerType: TriggerType;
  triggerSpec: TriggerSpec;
  onTriggerTypeChange: (type: TriggerType) => void;
  onTriggerSpecChange: (spec: TriggerSpec) => void;
}

const OPERATORS = [">", "<", ">=", "<=", "==", "!="];
const AGGREGATIONS = ["avg", "max", "min", "sum", "count"];
const DURATIONS = ["1m", "5m", "10m", "15m", "30m", "1h"];

export function TriggerSection({
  triggerType,
  triggerSpec,
  onTriggerTypeChange,
  onTriggerSpecChange,
}: TriggerSectionProps) {
  return (
    <div className="space-y-4 rounded-2xl p-4" style={{ border: "1px solid var(--border)", backgroundColor: "var(--surface-overlay)" }}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>트리거 설정 (필수)</h3>
      </div>

      <FormFieldGroup label="트리거 타입" required={true}>
        <div className="flex gap-2">
          {(["metric", "event", "schedule"] as const).map((type) => (
            <button
              key={type}
              onClick={() => onTriggerTypeChange(type)}
              className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors ${
                triggerType === type
                  ? "border-sky-500 bg-sky-500/20 text-sky-300"
                  : ""
              }`}
              style={triggerType !== type ? { border: "1px solid var(--border-muted)", backgroundColor: "rgba(30, 41, 59, 0.4)", color: "var(--muted-foreground)" } : undefined}
            >
              {type === "metric" && "📊 메트릭"}
              {type === "event" && "📢 이벤트"}
              {type === "schedule" && "⏰ 스케줄"}
            </button>
          ))}
        </div>
      </FormFieldGroup>

      {triggerType === "metric" && (
        <MetricTriggerForm
          spec={triggerSpec}
          onChange={onTriggerSpecChange}
        />
      )}

      {triggerType === "event" && (
        <EventTriggerForm spec={triggerSpec} onChange={onTriggerSpecChange} />
      )}

      {triggerType === "schedule" && (
        <ScheduleTriggerForm
          spec={triggerSpec}
          onChange={onTriggerSpecChange}
        />
      )}
    </div>
  );
}

function MetricTriggerForm({
  spec,
  onChange,
}: {
  spec: TriggerSpec;
  onChange: (spec: TriggerSpec) => void;
}) {
  return (
    <div className="space-y-3">
      <FormFieldGroup label="메트릭명" required={true}>
        <input
          type="text"
          value={spec.metricName || ""}
          onChange={(e) =>
            onChange({ ...spec, metricName: e.target.value })
          }
          placeholder="예: cpu_usage, memory_percent"
          className="w-full rounded-lg px-3 py-2 text-xs placeholder-slate-500" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
        />
      </FormFieldGroup>

      <div className="flex gap-3">
        <div className="flex-1">
          <FormFieldGroup label="연산자" required={true}>
            <select
              value={spec.operator || ">"}
              onChange={(e) =>
                onChange({ ...spec, operator: e.target.value })
              }
              className="w-full rounded-lg px-3 py-2 text-xs" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
            >
              {OPERATORS.map((op) => (
                <option key={op} value={op}>
                  {op}
                </option>
              ))}
            </select>
          </FormFieldGroup>
        </div>

        <div className="flex-1">
          <FormFieldGroup label="임계값" required={true}>
            <input
              type="number"
              value={spec.threshold || ""}
              onChange={(e) =>
                onChange({ ...spec, threshold: e.target.value })
              }
              placeholder="80"
              className="w-full rounded-lg px-3 py-2 text-xs" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
            />
          </FormFieldGroup>
        </div>
      </div>

      <div className="flex gap-3">
        <div className="flex-1">
          <FormFieldGroup label="집계 방식" required={true}>
            <select
              value={spec.aggregation || "avg"}
              onChange={(e) =>
                onChange({ ...spec, aggregation: e.target.value })
              }
              className="w-full rounded-lg px-3 py-2 text-xs" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
            >
              {AGGREGATIONS.map((agg) => (
                <option key={agg} value={agg}>
                  {agg}
                </option>
              ))}
            </select>
          </FormFieldGroup>
        </div>

        <div className="flex-1">
          <FormFieldGroup label="시간 윈도우" required={true}>
            <select
              value={spec.duration || "5m"}
              onChange={(e) =>
                onChange({ ...spec, duration: e.target.value })
              }
              className="w-full rounded-lg px-3 py-2 text-xs" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
            >
              {DURATIONS.map((dur) => (
                <option key={dur} value={dur}>
                  {dur}
                </option>
              ))}
            </select>
          </FormFieldGroup>
        </div>
      </div>
    </div>
  );
}

function EventTriggerForm({
  spec,
  onChange,
}: {
  spec: TriggerSpec;
  onChange: (spec: TriggerSpec) => void;
}) {
  return (
    <div className="space-y-3">
      <FormFieldGroup label="이벤트 타입" required={true}>
        <input
          type="text"
          value={spec.eventType || ""}
          onChange={(e) =>
            onChange({ ...spec, eventType: e.target.value })
          }
          placeholder="예: error, warning, alert"
          className="w-full rounded-lg px-3 py-2 text-xs placeholder-slate-500" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
        />
      </FormFieldGroup>
    </div>
  );
}

function ScheduleTriggerForm({
  spec,
  onChange,
}: {
  spec: TriggerSpec;
  onChange: (spec: TriggerSpec) => void;
}) {
  return (
    <div className="space-y-3">
      <FormFieldGroup
        label="Cron 표현식"
        required={true}
        help="예: 0 9 * * * (매일 9시)"
      >
        <input
          type="text"
          value={spec.scheduleExpression || ""}
          onChange={(e) =>
            onChange({ ...spec, scheduleExpression: e.target.value })
          }
          placeholder="0 9 * * *"
          className="w-full rounded-lg px-3 py-2 text-xs placeholder-slate-500" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
        />
      </FormFieldGroup>
    </div>
  );
}
