"use client";

import { FormFieldGroup } from "./FormFieldGroup";

interface BasicInfoSectionProps {
  ruleName: string;
  description: string;
  isActive: boolean;
  onRuleNameChange: (name: string) => void;
  onDescriptionChange: (description: string) => void;
  onActiveChange: (active: boolean) => void;
}

export function BasicInfoSection({
  ruleName,
  description,
  isActive,
  onRuleNameChange,
  onDescriptionChange,
  onActiveChange,
}: BasicInfoSectionProps) {
  return (
    <div className="space-y-4 rounded-2xl p-4" style={{ border: "1px solid var(--border)", backgroundColor: "var(--surface-overlay)" }}>
      <h3 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>기본 정보</h3>

      <FormFieldGroup
        label="규칙명"
        required={true}
        error={ruleName.length === 0 ? "규칙명을 입력하세요" : undefined}
      >
        <input
          type="text"
          value={ruleName}
          onChange={(e) => onRuleNameChange(e.target.value)}
          placeholder="예: CPU 고가용 모니터링"
          className="w-full rounded-lg px-3 py-2 text-sm placeholder-slate-500 focus:border-sky-500 focus:outline-none" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
        />
      </FormFieldGroup>

      <FormFieldGroup
        label="설명"
        help="규칙의 목적과 동작을 설명하세요"
      >
        <textarea
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="이 규칙은..."
          rows={3}
          className="w-full rounded-lg px-3 py-2 text-sm placeholder-slate-500 focus:border-sky-500 focus:outline-none" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)" }}
        />
      </FormFieldGroup>

      <div className="flex items-center gap-3 rounded-lg p-3" style={{ border: "1px solid var(--border-muted)", backgroundColor: "rgba(30, 41, 59, 0.4)" }}>
        <input
          type="checkbox"
          id="isActive"
          checked={isActive}
          onChange={(e) => onActiveChange(e.target.checked)}
          className="rounded"
        />
        <label
          htmlFor="isActive"
          className="flex-1 text-sm font-medium cursor-pointer" style={{ color: "var(--foreground)" }}
        >
          규칙 활성화
        </label>
        <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
          {isActive ? "활성" : "비활성"}
        </span>
      </div>
    </div>
  );
}
