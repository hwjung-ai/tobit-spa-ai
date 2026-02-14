"use client";

import { cn } from "@/lib/utils";

type TriggerType = "metric" | "event" | "schedule" | "anomaly";

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
    <div className="cep-section-container">
      <div className="cep-section-header">
        <h3 className="cep-section-title">트리거 설정 (필수)</h3>
      </div>

      <FormFieldGroup label="트리거 타입" required={true}>
        <div className="flex gap-2">
          {(["metric", "event", "schedule", "anomaly"] as const).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => onTriggerTypeChange(type)}
              className={cn(
                "px-3 py-2 rounded-lg text-xs font-medium border transition-colors",
                triggerType === type
                  ? "border-sky-500 bg-sky-500/20 text-sky-300"
                  : "border-border-muted bg-slate-600/40 text-muted-foreground hover:border-sky-400/50"
              )}
            >
              {type === "metric" && "📊 메트릭"}
              {type === "event" && "📢 이벤트"}
              {type === "schedule" && "⏰ 스케줄"}
              {type === "anomaly" && "🔍 이상탐지"}
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

      {triggerType === "anomaly" && (
        <AnomalyTriggerForm
          spec={triggerSpec}
          onChange={onTriggerSpecChange}
        />
      )}
    </div>
  );
}

function AnomalyTriggerForm({
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
          placeholder="예: cpu_usage, response_time"
          className="cep-input-full-lg"
        />
      </FormFieldGroup>

      <FormFieldGroup label="탐지 민감도" help="높을수록 더 많은 이상을 탐지합니다">
        <select
          value={spec.aggregation || "medium"}
          onChange={(e) =>
            onChange({ ...spec, aggregation: e.target.value })
          }
          className="cep-select-primary w-full"
        >
          <option value="low">낮음 (중요 이상만)</option>
          <option value="medium">중간</option>
          <option value="high">높음 (미세한 변화도 탐지)</option>
        </select>
      </FormFieldGroup>

      <FormFieldGroup label="관측 기간">
        <select
          value={spec.duration || "1h"}
          onChange={(e) =>
            onChange({ ...spec, duration: e.target.value })
          }
          className="cep-select-primary w-full"
        >
          {["15m", "30m", "1h", "6h", "24h"].map((dur) => (
            <option key={dur} value={dur}>
              {dur}
            </option>
          ))}
        </select>
      </FormFieldGroup>
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
          className="cep-input-full-lg"
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
              className="cep-select-primary w-full"
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
              className="cep-input-full-lg"
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
              className="cep-select-primary w-full"
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
              className="cep-select-primary w-full"
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
          className="cep-input-full-lg"
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
          className="cep-input-full-lg"
        />
      </FormFieldGroup>
    </div>
  );
}
