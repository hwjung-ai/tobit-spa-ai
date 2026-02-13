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
    <div className="flex h-full flex-col border-l transition-all duration-200" data-testid="copilot-panel">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <p className="draft-panel-label">Copilot</p>
          <p className="text-xs">Patch suggestions</p>
        </div>
        <span className="draft-panel-label">
          {previewStatusLabel}
        </span>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        <div className="draft-panel-section">
          <p className="draft-panel-label">Context</p>
          <div className="mt-2 space-y-1 text-xs">
            <p>Screen ID: {screenId}</p>
            <p>Stage: {stage}</p>
            <p>Summary: {schemaSummary}</p>
            <p>Component: {selectedComponentId ?? "none"}</p>
          </div>
        </div>

        <textarea
          aria-label="Copilot prompt"
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          placeholder="Describe what you want to change..."
          className="h-24 w-full rounded-2xl border px-3 py-2 text-sm outline-none transition focus:border-sky-500"

        />

        <button
          onClick={handleGenerateProposal}
          disabled={!inputValue.trim()}
          className="w-full rounded-2xl bg-sky-600 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-white transition hover:bg-sky-500 disabled:opacity-40"
        >
          Generate Proposal
        </button>

        <div className="draft-panel-section">
          <p className="draft-panel-label">Patch output (RFC6902)</p>
          <p className="text-xs mt-2">
            Provide a JSON Patch array (or wrap it in {"{"} patch: [...] {"}"}) referencing ScreenSchemaV1.
          </p>
          <Textarea
            value={patchText}
            onChange={(event) => {
              setPatchText(event.target.value);
              setLocalError(null);
            }}
            placeholder='e.g. [{"op":"replace","path":"/components/0/props/label","value":"New"}]'
            className="code-block max-h-48 w-full rounded-xl px-3 py-2 text-xs font-mono outline-none"

          />
        </div>

        {visibleError && (
          <div className="alert-box alert-error">
            {visibleError}
          </div>
        )}
      </div>

      <div className="px-4 py-3 space-y-2">
        <button
          onClick={handlePreviewToggle}
          className="draft-panel-button w-full"
        >
          {previewEnabled ? "Hide Preview" : "Preview Patch"}
        </button>
        <button
          onClick={handleApply}
          className="draft-panel-button w-full bg-emerald-600 hover:bg-emerald-500 text-white"

        >
          Apply to Draft
        </button>
        <button
          onClick={handleDiscard}
          className="draft-panel-button w-full"
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
