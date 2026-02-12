"use client";

import React, { useMemo, useState } from "react";
import { JsonPatchOperation } from "@/lib/ui-screen/json-patch";
import { useEditorState } from "@/lib/ui-screen/editor-state";

interface CopilotPanelProps {
  screenId: string;
  stage: string;
  schemaSummary: string;
  selectedComponentId: string | null;
}

type PatchParseResult = {
  patch: JsonPatchOperation[] | null;
  error: string | null;
};

function parsePatchText(text: string): PatchParseResult {
  if (!text || !text.trim()) {
    return { patch: null, error: "No patch text provided" };
  }
  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) {
      return { patch: parsed, error: null };
    }
    if (parsed && Array.isArray(parsed.patch)) {
      return { patch: parsed.patch, error: null };
    }
    return { patch: null, error: "Patch must be an array or { patch: [...] } object" };
  } catch (error) {
    return { patch: null, error: `Invalid JSON: ${error instanceof Error ? error.message : String(error)}` };
  }
}

export default function ScreenEditorCopilotPanel({
  screenId,
  stage,
  schemaSummary,
  selectedComponentId,
}: CopilotPanelProps) {
  const editorState = useEditorState();
  const [inputValue, setInputValue] = useState("");
  const [patchText, setPatchText] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const parseResult = useMemo(() => parsePatchText(patchText), [patchText]);
  const previewEnabled = editorState.previewEnabled;

  const contextPayload = useMemo(() => {
    return {
      screen_id: screenId,
      stage,
      schema_summary: schemaSummary,
      selected_component: selectedComponentId,
    };
  }, [screenId, schemaSummary, selectedComponentId, stage]);

  const handleGenerateProposal = () => {
    if (!inputValue.trim()) {
      return;
    }
    const payload = {
      ...contextPayload,
      prompt: inputValue.trim(),
    };
    setPatchText(JSON.stringify({ patch: [], context: payload }, null, 2));
    setLocalError(null);
  };

  const handlePreviewToggle = () => {
    if (!parseResult.patch) {
      setLocalError(parseResult.error);
      return;
    }
    setLocalError(null);
    editorState.setProposedPatch(JSON.stringify(parseResult.patch));
    if (previewEnabled) {
      editorState.disablePreview();
    } else {
      editorState.previewPatch();
    }
  };

  const handleApply = () => {
    if (!parseResult.patch) {
      setLocalError(parseResult.error);
      return;
    }
    setLocalError(null);
    editorState.setProposedPatch(JSON.stringify(parseResult.patch));
    try {
      editorState.applyProposedPatch();
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error));
    }
  };

  const handleDiscard = () => {
    setPatchText("");
    setLocalError(null);
    editorState.discardProposal();
  };

  const previewStatusLabel = previewEnabled ? "Preview ON" : "Preview OFF";
  const visibleError = localError || editorState.previewError;

  return (
    <div
      className="flex h-full flex-col border-l  transition-all duration-200" style={{color: "var(--foreground)", borderLeft: "1px solid var(--border)", backgroundColor: "var(--surface-base)"}}
      data-testid="copilot-panel"
    >
      <div className="flex items-center justify-between border-b px-4 py-3" style={{borderBottom: "1px solid var(--border)"}}>
        <div>
          <p className="text-xs uppercase tracking-[0.3em]" style={{color: "var(--muted-foreground)"}}>Copilot</p>
          <p className="text-[11px]" style={{color: "var(--muted-foreground)"}}>Patch suggestions</p>
        </div>
        <span className="text-[11px] uppercase tracking-[0.3em]" style={{color: "var(--muted-foreground)"}}>
          {previewStatusLabel}
        </span>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        <div className="space-y-1 text-[10px]" style={{color: "var(--muted-foreground)"}}>
          <p>Screen ID: {screenId}</p>
          <p>Stage: {stage}</p>
          <p>Summary: {schemaSummary}</p>
          <p>Component: {selectedComponentId ?? "none"}</p>
        </div>

        <textarea
          aria-label="Copilot prompt"
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          placeholder="Describe what you want to change..."
          className="h-24 w-full rounded-2xl border px-3 py-2 text-sm outline-none transition focus:border-sky-500"
          style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)"}}
        />

        <button
          onClick={handleGenerateProposal}
          disabled={!inputValue.trim()}
          className="w-full rounded-2xl bg-sky-600 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-white transition hover:bg-sky-500 disabled:opacity-40"
        >
          Generate Proposal
        </button>

        <div className="space-y-1 rounded-2xl border p-3 text-xs" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)", color: "var(--muted-foreground)"}}>
          <p className="text-[10px] uppercase tracking-[0.3em]" style={{color: "var(--muted-foreground)"}}>Patch output (RFC6902)</p>
          <p className="text-[10px]" style={{color: "var(--muted-foreground)"}}>
            Provide a JSON Patch array (or wrap it in {"{"} patch: [...] {"}"}) referencing ScreenSchemaV1.
          </p>
          <Textarea
            value={patchText}
            onChange={(event) => {
              setPatchText(event.target.value);
              setLocalError(null);
            }}
            placeholder='e.g. [{"op":"replace","path":"/components/0/props/label","value":"New"}]'
            className="max-h-48 w-full rounded-xl border px-3 py-2 text-[10px] font-mono outline-none"
            style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)"}}
          />
        </div>

        {visibleError && (
          <div className="rounded-2xl border border-red-800 bg-red-950/60 p-3 text-[10px] text-red-300">
            {visibleError}
          </div>
        )}
      </div>

      <div className="px-4 py-3 space-y-2" style={{borderTop: "1px solid var(--border)"}}>
        <button
          onClick={handlePreviewToggle}
          className="w-full rounded-2xl px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-white transition"
          style={{backgroundColor: "var(--surface-elevated)"}}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = "var(--surface-overlay)"}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = "var(--surface-elevated)"}
        >
          {previewEnabled ? "Hide Preview" : "Preview Patch"}
        </button>
        <button
          onClick={handleApply}
          className="w-full rounded-2xl bg-emerald-600 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-white transition hover:bg-emerald-500"
        >
          Apply to Draft
        </button>
        <button
          onClick={handleDiscard}
          className="w-full rounded-2xl border px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] transition"
          style={{borderColor: "var(--border)", color: "var(--muted-foreground)"}}
          onMouseEnter={(e) => e.currentTarget.style.borderColor = "var(--primary)"}
          onMouseLeave={(e) => e.currentTarget.style.borderColor = "var(--border)"}
        >
          Discard Proposal
        </button>
      </div>
    </div>
  );
}

function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea {...props} />
  );
}
