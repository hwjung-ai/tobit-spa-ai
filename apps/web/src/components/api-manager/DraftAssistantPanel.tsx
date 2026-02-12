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
      <div className="draft-panel">
        <div className="draft-panel-section">
          <p className="draft-panel-label">Scenario Functions</p>
          <div className="mt-2 space-y-2">
            {scenarioFunctions.map((fn) => (
              <div key={fn.name} className="draft-panel-item">
                <p className="draft-panel-item-label">{fn.name}</p>
                <p className="draft-panel-item-description">{fn.summary}</p>
                <p className="draft-panel-item-signature">{fn.signature}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-between">
          <span className="draft-panel-label">Draft status</span>
          <span className="text-sm font-semibold" style={{color: "var(--foreground)"}}>
            {draftStatusLabels[draftStatus] ?? draftStatus}
          </span>
        </div>
        {draftNotes ? <p className="text-sm" style={{color: "var(--muted-foreground)"}}>{draftNotes}</p> : null}
        {draftDiff ? (
          <ul className="space-y-1 text-xs" style={{color: "var(--muted-foreground)"}}>
            {draftDiff.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        ) : null}
        {draftStatus === "outdated" ? (
          <div className="alert-info">
            Draft is outdated. Apply again or regenerate.
          </div>
        ) : null}
        <div className="grid gap-2 sm:grid-cols-2">
          <button
            onClick={onPreviewDraft}
            className="draft-panel-button"
          >
            Preview
          </button>
          <button
            onClick={onTestDraft}
            className="draft-panel-button"
          >
            Test (Dry-run)
          </button>
          <button
            onClick={onApplyDraft}
            className="draft-panel-button"
            disabled={!draftApi || draftTestOk !== true}
          >
            Apply
          </button>
          <button
            onClick={onSaveLocalDraft}
            className="draft-panel-button bg-emerald-500/70 hover:bg-emerald-400"
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
          <div className="alert-box alert-error">
            {draftErrors.map((error) => (
              <p key={error}>{error}</p>
            ))}
          </div>
        )}
        {draftWarnings.length > 0 && (
          <div className="alert-box alert-warning">
            {draftWarnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        )}
        {previewSummary && previewJson ? (
          <div className="draft-panel-section space-y-2">
            <p className="draft-panel-label">Preview</p>
            <p className="text-sm" style={{color: "var(--foreground)"}}>{previewSummary}</p>
            <pre className="code-block code-block-lg">
              {previewJson}
            </pre>
          </div>
        ) : null}
        {showDebug ? (
          <details className="debug-section">
            <summary className="debug-section-summary">
              Debug
            </summary>
            <div className="debug-section-content">
              <p className="debug-section-label">
                Save target: {saveTarget ?? "none"}
              </p>
              {lastSaveError ? (
                <p className="text-xs text-rose-300">Save error: {lastSaveError}</p>
              ) : null}
              <p className="debug-section-label">Selected API</p>
              <p className="debug-section-value">
                {selectedApi ? `${selectedApi.api_name} (${selectedApi.api_id})` : "새 API"}
              </p>
              <p className="debug-section-label">
                Parse status: {lastParseStatus}
              </p>
              {lastParseError ? (
                <p className="text-xs text-rose-300">Error: {lastParseError}</p>
              ) : null}
              <p className="debug-section-label">Last assistant raw</p>
              <pre className="code-block">
                {lastAssistantRaw || "없음"}
              </pre>
              {draftApi ? (
                <>
                  <p className="debug-section-label">Draft JSON</p>
                  <pre className="code-block">
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
