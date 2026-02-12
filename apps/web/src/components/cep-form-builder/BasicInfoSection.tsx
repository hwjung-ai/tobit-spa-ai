"use client";

interface BasicInfoSectionProps {
  ruleName: string;
  ruleDescription: string;
  isEnabled: boolean;
  onNameChange: (name: string) => void;
  onDescriptionChange: (description: string) => void;
  onEnabledChange: (enabled: boolean) => void;
}

export function BasicInfoSection({
  ruleName,
  ruleDescription,
  isEnabled,
  onNameChange,
  onDescriptionChange,
  onEnabledChange,
}: BasicInfoSectionProps) {
  return (
    <div className="cep-section-container">
      <h3 className="cep-section-title">기본 정보</h3>

      <div className="space-y-3">
        <div className="space-y-1">
          <label className="cep-window-label">규칙명 (필수)</label>
          <input
            type="text"
            value={ruleName}
            onChange={(e) => onNameChange(e.target.value)}
            placeholder="규칙 이름을 입력하세요"
            className="cep-input-full-lg"
          />
        </div>

        <div className="space-y-1">
          <label className="cep-window-label">설명</label>
          <textarea
            value={ruleDescription}
            onChange={(e) => onDescriptionChange(e.target.value)}
            placeholder="규칙에 대한 설명을 입력하세요"
            className="cep-input-full-lg"
          />
        </div>

        <div className="cep-toggle-container">
          <label className="cep-toggle-label">활성화</label>
          <input
            type="checkbox"
            checked={isEnabled}
            onChange={(e) => onEnabledChange(e.target.checked)}
            className="h-4 w-4 rounded"
          />
        </div>
      </div>
    </div>
  );
}
