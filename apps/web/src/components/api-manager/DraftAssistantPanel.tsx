"use client";

import BuilderCopilotPanel from "@/components/chat/BuilderCopilotPanel";
import type { ApiDefinitionItem, ApiDraft, DraftStatus } from "@/lib/api-manager/types";

interface DraftAssistantPanelProps {
  instructionPrompt: string;
  scenarioFunctions: Array<{ name: string; summary: string; signature: string }>;
  builderContext?: Record<string, unknown> | null;
  onAssistantMessage: (messageText: string) => void;
  onAssistantMessageComplete: (messageText: string) => void;
  onUserMessage: () => void;
  draftStatusLabels: Record<string, string>;
  draftStatus: DraftStatus;
  draftNotes: string | null;
  draftDiff: string[] | null;
  draftApi: ApiDraft | null;
  draftTestOk: boolean | null;
  draftErrors: string[];
  draftWarnings: string[];
  previewSummary: string | null;
  previewJson: string | null;
  showDebug: boolean;
  saveTarget: "server" | "local" | null;
  lastSaveError: string | null;
  selectedApi: ApiDefinitionItem | null;
  lastParseStatus: "idle" | "success" | "fail";
  lastParseError: string | null;
  lastAssistantRaw: string;
  onPreviewDraft: () => void;
  onTestDraft: () => void;
  onApplyDraft: () => void;
  onSaveLocalDraft: () => void;
}

export default function DraftAssistantPanel({
  instructionPrompt,
  scenarioFunctions,
  builderContext,
  onAssistantMessage,
  onAssistantMessageComplete,
  onUserMessage,
  draftStatusLabels,
  draftStatus,
  draftNotes,
  draftDiff,
  draftApi,
  draftTestOk,
  draftErrors,
  draftWarnings,
  previewSummary,
  previewJson,
  showDebug,
  saveTarget,
  lastSaveError,
  selectedApi,
  lastParseStatus,
  lastParseError,
  lastAssistantRaw,
  onPreviewDraft,
  onTestDraft,
  onApplyDraft,
  onSaveLocalDraft,
}: DraftAssistantPanelProps) {
  return (
    <div className="space-y-4">
      <BuilderCopilotPanel
        instructionPrompt={instructionPrompt}
        expectedContract="api_draft"
        builderContext={builderContext}
        onAssistantMessage={onAssistantMessage}
        onAssistantMessageComplete={onAssistantMessageComplete}
        onUserMessage={onUserMessage}
        inputPlaceholder="API 드래프트를 설명해 주세요..."
      />
      <div className="space-y-3 rounded-3xl p-4 text-sm" style={{border: "1px solid var(--border)", backgroundColor: "rgba(15, 23, 42, 0.6)", color: "var(--muted-foreground)"}}>
        <div className="rounded-2xl p-3" style={{border: "1px solid var(--border)", backgroundColor: "rgba(15, 23, 42, 0.4)"}}>
          <p className="text-[11px] uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>Scenario Functions</p>
          <div className="mt-2 space-y-2">
            {scenarioFunctions.map((fn) => (
              <div key={fn.name} className="rounded-xl px-2 py-1.5" style={{border: "1px solid rgba(30, 41, 59, 0.8)", backgroundColor: "rgba(15, 23, 42, 0.4)"}}>
                <p className="text-[11px] font-semibold" style={{color: "var(--muted-foreground)"}}>{fn.name}</p>
                <p className="text-[10px]" style={{color: "var(--muted-foreground)"}}>{fn.summary}</p>
                <p className="text-[10px] text-sky-300">{fn.signature}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>Draft status</span>
          <span className="text-sm font-semibold" style={{color: "var(--foreground)"}}>
            {draftStatusLabels[draftStatus] ?? draftStatus}
          </span>
        </div>
        {draftNotes ? <p className="text-sm" style={{color: "var(--muted-foreground)"}}>{draftNotes}</p> : null}
        {draftDiff ? (
          <ul className="space-y-1 text-[11px]" style={{color: "var(--muted-foreground)"}}>
            {draftDiff.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        ) : null}
        {draftStatus === "outdated" ? (
          <div className="rounded-2xl border border-amber-500/60 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200">
            Draft is outdated. Apply again or regenerate.
          </div>
        ) : null}
        <div className="grid gap-2 sm:grid-cols-2">
          <button
            onClick={onPreviewDraft}
            className="rounded-2xl px-3 py-2 text-[11px] font-semibold uppercase tracking-normal transition hover:border-sky-500" style={{border: "1px solid var(--border)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)"}}
          >
            Preview
          </button>
          <button
            onClick={onTestDraft}
            className="rounded-2xl border   px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-emerald-400" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}
          >
            Test (Dry-run)
          </button>
          <button
            onClick={onApplyDraft}
            className="rounded-2xl border   px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-indigo-400" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}
            disabled={!draftApi || draftTestOk !== true}
          >
            Apply
          </button>
          <button
            onClick={onSaveLocalDraft}
            className="rounded-2xl border  bg-emerald-500/70 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:bg-emerald-400" style={{borderColor: "var(--border)"}}
            disabled={!draftApi || draftTestOk !== true}
          >
            Save (Local)
          </button>
        </div>
        {!draftApi && (
          <p className="text-xs" style={{color: "var(--muted-foreground)"}}>
            No draft yet. Ask the copilot to generate one.
            {lastParseError ? ` Parse error: ${lastParseError}` : ""}
          </p>
        )}
        {draftErrors.length > 0 && (
          <div className="space-y-1 rounded-2xl border border-rose-500/60 bg-rose-500/5 px-3 py-2 text-[11px] text-rose-200">
            {draftErrors.map((error) => (
              <p key={error}>{error}</p>
            ))}
          </div>
        )}
        {draftWarnings.length > 0 && (
          <div className="space-y-1 rounded-2xl border border-amber-500/60 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-200">
            {draftWarnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        )}
        {previewSummary && previewJson ? (
          <div className="space-y-2 rounded-2xl p-3 text-[11px]" style={{border: "1px solid var(--border)", backgroundColor: "rgba(15, 23, 42, 0.4)", color: "var(--muted-foreground)"}}>
            <p className="text-xs uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>Preview</p>
            <p className="text-sm" style={{color: "var(--foreground)"}}>{previewSummary}</p>
            <pre className="max-h-48 overflow-auto rounded-xl p-2 text-[11px] custom-scrollbar" style={{backgroundColor: "rgba(15, 23, 42, 0.5)", color: "var(--muted-foreground)"}}>
              {previewJson}
            </pre>
          </div>
        ) : null}
        {showDebug ? (
          <details className="rounded-2xl p-3 text-[11px]" style={{border: "1px solid var(--border)", backgroundColor: "rgba(15, 23, 42, 0.4)", color: "var(--muted-foreground)"}}>
            <summary className="cursor-pointer text-xs uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>
              Debug
            </summary>
            <div className="mt-2 space-y-1">
              <p className="text-[10px] uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>
                Save target: {saveTarget ?? "none"}
              </p>
              {lastSaveError ? (
                <p className="text-[11px] text-rose-300">Save error: {lastSaveError}</p>
              ) : null}
              <p className="text-[10px] uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>Selected API</p>
              <p className="text-[11px]" style={{color: "var(--muted-foreground)"}}>
                {selectedApi ? `${selectedApi.api_name} (${selectedApi.api_id})` : "새 API"}
              </p>
              <p className="text-[10px] uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>
                Parse status: {lastParseStatus}
              </p>
              {lastParseError ? (
                <p className="text-[11px] text-rose-300">Error: {lastParseError}</p>
              ) : null}
              <p className="text-[10px] uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>Last assistant raw</p>
              <pre className="max-h-32 overflow-auto rounded-xl p-2 text-[10px]" style={{backgroundColor: "var(--surface-overlay)", color: "var(--muted-foreground)"}}>
                {lastAssistantRaw || "없음"}
              </pre>
              {draftApi ? (
                <>
                  <p className="text-[10px] uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>Draft JSON</p>
                  <pre className="max-h-32 overflow-auto rounded-xl  p-2 text-[10px]  custom-scrollbar" style={{color: "var(--foreground-secondary)", backgroundColor: "var(--surface-overlay)"}}>
                    {JSON.stringify(draftApi, null, 2)}
                  </pre>
                </>
              ) : null}
            </div>
          </details>
        ) : null}
      </div>
    </div>
  );
}
