"use client";

import ChatExperience from "./ChatExperience";
import type { CopilotContract } from "@/lib/copilot/contract-utils";

interface BuilderCopilotPanelProps {
  builderSlug?: string;
  instructionPrompt?: string;
  expectedContract?: CopilotContract;
  builderContext?: Record<string, unknown> | null;
  enableAutoRepair?: boolean;
  onAssistantMessage?: (text: string) => void;
  onAssistantMessageComplete?: (text: string) => void;
  onUserMessage?: (text: string) => void;
  inputPlaceholder?: string;
}

export default function BuilderCopilotPanel({
  builderSlug = "api-manager",
  instructionPrompt,
  expectedContract,
  builderContext,
  enableAutoRepair = true,
  onAssistantMessage,
  onAssistantMessageComplete,
  onUserMessage,
  inputPlaceholder,
}: BuilderCopilotPanelProps) {
  return (
    <div className="shadow-inner shadow-black/20" aria-live="polite">
      <ChatExperience
        builderSlug={builderSlug}
        inline
        instructionPrompt={instructionPrompt}
        expectedContract={expectedContract}
        builderContext={builderContext}
        enableAutoRepair={enableAutoRepair}
        onAssistantMessage={onAssistantMessage}
        onAssistantMessageComplete={onAssistantMessageComplete}
        onUserMessage={onUserMessage}
        inputPlaceholder={inputPlaceholder}
      />
    </div>
  );
}
