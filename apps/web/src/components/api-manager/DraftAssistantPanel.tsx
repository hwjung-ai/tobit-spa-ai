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
      <div className="space-y-3 rounded-3xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300">
        <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-3">
          <p className="text-[11px] uppercase tracking-normal text-slate-500">Scenario Functions</p>
          <div className="mt-2 space-y-2">
            {scenarioFunctions.map((fn) => (
              <div key={fn.name} className="rounded-xl border border-slate-800/80 bg-slate-900/40 px-2 py-1.5">
                <p className="text-[11px] font-semibold text-slate-100">{fn.name}</p>
                <p className="text-[10px] text-slate-400">{fn.summary}</p>
                <p className="text-[10px] text-sky-300">{fn.signature}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-normal text-slate-500">Draft status</span>
          <span className="text-sm font-semibold text-white">
            {draftStatusLabels[draftStatus] ?? draftStatus}
          </span>
        </div>
        {draftNotes ? <p className="text-sm text-slate-300">{draftNotes}</p> : null}
        {draftDiff ? (
          <ul className="space-y-1 text-[11px] text-slate-400">
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
            className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-sky-500"
          >
            Preview
          </button>
          <button
            onClick={onTestDraft}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-emerald-400"
          >
            Test (Dry-run)
          </button>
          <button
            onClick={onApplyDraft}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-indigo-400"
            disabled={!draftApi || draftTestOk !== true}
          >
            Apply
          </button>
          <button
            onClick={onSaveLocalDraft}
            className="rounded-2xl border border-slate-800 bg-emerald-500/70 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:bg-emerald-400"
            disabled={!draftApi || draftTestOk !== true}
          >
            Save (Local)
          </button>
        </div>
        {!draftApi && (
          <p className="text-xs text-slate-400">
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
          <div className="space-y-2 rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-[11px] text-slate-200">
            <p className="text-xs uppercase tracking-normal text-slate-500">Preview</p>
            <p className="text-sm text-white">{previewSummary}</p>
            <pre className="max-h-48 overflow-auto rounded-xl bg-slate-900/50 p-2 text-[11px] text-slate-300 custom-scrollbar">
              {previewJson}
            </pre>
          </div>
        ) : null}
        {showDebug ? (
          <details className="rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-[11px] text-slate-300">
            <summary className="cursor-pointer text-xs uppercase tracking-normal text-slate-400">
              Debug
            </summary>
            <div className="mt-2 space-y-1">
              <p className="text-[10px] uppercase tracking-normal text-slate-500">
                Save target: {saveTarget ?? "none"}
              </p>
              {lastSaveError ? (
                <p className="text-[11px] text-rose-300">Save error: {lastSaveError}</p>
              ) : null}
              <p className="text-[10px] uppercase tracking-normal text-slate-500">Selected API</p>
              <p className="text-[11px] text-slate-200">
                {selectedApi ? `${selectedApi.api_name} (${selectedApi.api_id})` : "새 API"}
              </p>
              <p className="text-[10px] uppercase tracking-normal text-slate-500">
                Parse status: {lastParseStatus}
              </p>
              {lastParseError ? (
                <p className="text-[11px] text-rose-300">Error: {lastParseError}</p>
              ) : null}
              <p className="text-[10px] uppercase tracking-normal text-slate-500">Last assistant raw</p>
              <pre className="max-h-32 overflow-auto rounded-xl bg-slate-900/60 p-2 text-[10px] text-slate-200">
                {lastAssistantRaw || "없음"}
              </pre>
              {draftApi ? (
                <>
                  <p className="text-[10px] uppercase tracking-normal text-slate-500">Draft JSON</p>
                  <pre className="max-h-32 overflow-auto rounded-xl bg-slate-900/60 p-2 text-[10px] text-slate-200 custom-scrollbar">
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
