"use client";

import ChatExperience from "./ChatExperience";

interface BuilderCopilotPanelProps {
  builderSlug?: string;
  instructionPrompt?: string;
  onAssistantMessage?: (text: string) => void;
  onAssistantMessageComplete?: (text: string) => void;
  onUserMessage?: (text: string) => void;
  inputPlaceholder?: string;
}

export default function BuilderCopilotPanel({
  builderSlug = "api-manager",
  instructionPrompt,
  onAssistantMessage,
  onAssistantMessageComplete,
  onUserMessage,
  inputPlaceholder,
}: BuilderCopilotPanelProps) {
  return (
    <div className="shadow-inner shadow-black/20">
      <ChatExperience
        builderSlug={builderSlug}
        inline
        instructionPrompt={instructionPrompt}
        onAssistantMessage={onAssistantMessage}
        onAssistantMessageComplete={onAssistantMessageComplete}
        onUserMessage={onUserMessage}
        inputPlaceholder={inputPlaceholder}
      />
    </div>
  );
}
