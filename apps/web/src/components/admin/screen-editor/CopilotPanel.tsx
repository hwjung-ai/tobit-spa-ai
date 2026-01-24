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
      className="flex h-full flex-col border-l border-slate-800 bg-slate-950 text-slate-100 transition-all duration-200"
      data-testid="copilot-panel"
    >
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Copilot</p>
          <p className="text-[11px] text-slate-300">Patch suggestions</p>
        </div>
        <span className="text-[11px] uppercase tracking-[0.3em] text-slate-400">
          {previewStatusLabel}
        </span>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        <div className="space-y-1 text-[10px] text-slate-500">
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
          className="h-24 w-full rounded-2xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
        />

        <button
          onClick={handleGenerateProposal}
          disabled={!inputValue.trim()}
          className="w-full rounded-2xl bg-sky-600 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-white transition hover:bg-sky-500 disabled:opacity-40"
        >
          Generate Proposal
        </button>

        <div className="space-y-1 rounded-2xl border border-slate-800 bg-slate-900/60 p-3 text-xs text-slate-300">
          <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Patch output (RFC6902)</p>
          <p className="text-[10px] text-slate-500">
            Provide a JSON Patch array (or wrap it in {"{"} patch: [...] {"}"}) referencing ScreenSchemaV1.
          </p>
          <Textarea
            value={patchText}
            onChange={(event) => {
              setPatchText(event.target.value);
              setLocalError(null);
            }}
            placeholder='e.g. [{"op":"replace","path":"/components/0/props/label","value":"New"}]'
            className="max-h-48 w-full rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[10px] font-mono text-slate-100 outline-none"
          />
        </div>

        {visibleError && (
          <div className="rounded-2xl border border-red-800 bg-red-950/60 p-3 text-[10px] text-red-300">
            {visibleError}
          </div>
        )}
      </div>

      <div className="border-t border-slate-800 px-4 py-3 space-y-2">
        <button
          onClick={handlePreviewToggle}
          className="w-full rounded-2xl bg-slate-800 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-white transition hover:bg-slate-700"
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
          className="w-full rounded-2xl border border-slate-700 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400 transition hover:border-slate-500"
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
