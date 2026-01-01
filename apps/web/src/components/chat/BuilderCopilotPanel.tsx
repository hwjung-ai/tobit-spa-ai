"use client";

import ChatExperience from "./ChatExperience";

interface BuilderCopilotPanelProps {
  builderSlug?: string;
  instructionPrompt?: string;
  onAssistantMessage?: (text: string) => void;
  onAssistantMessageComplete?: (text: string) => void;
}

export default function BuilderCopilotPanel({
  builderSlug = "api-manager",
  instructionPrompt,
  onAssistantMessage,
  onAssistantMessageComplete,
}: BuilderCopilotPanelProps) {
  return (
    <div className="space-y-4 rounded-3xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-300 shadow-inner shadow-black/40">
      <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Builder Copilot</p>
      <ChatExperience
        builderSlug={builderSlug}
        inline
        instructionPrompt={instructionPrompt}
        onAssistantMessage={onAssistantMessage}
        onAssistantMessageComplete={onAssistantMessageComplete}
      />
    </div>
  );
}
