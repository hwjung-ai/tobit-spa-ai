"use client";

import React, { useMemo, useState } from "react";
import { JsonPatchOperation } from "@/lib/ui-screen/json-patch";
import { useEditorState } from "@/lib/ui-screen/editor-state";

interface CopilotPanelProps {
  screenId: string;
  stage: string;
  schemaSummary: string;
  selectedComponentId: string | null;
  screenSchema: Record<string, unknown>;
  availableHandlers?: string[];
  statePaths?: string[];
}

interface PatchParseResult {
  patch: JsonPatchOperation[] | null;
  error: string | null;
}

interface CopilotResponse {
  patch: JsonPatchOperation[];
  explanation: string;
  confidence: number;
  suggestions: string[];
}

const QUICK_ACTIONS = [
  { label: "🔵 버튼 추가", prompt: "파란색 버튼 하나 추가해줘" },
  { label: "📝 입력 필드", prompt: "입력 필드를 추가해줘" },
  { label: "📊 테이블", prompt: "데이터 테이블을 추가해줘" },
  { label: "🎨 색상 변경", prompt: "선택한 컴포넌트의 색상을 파란색으로 변경해줘" },
  { label: "📐 레이아웃", prompt: "컴포넌트들을 2열 레이아웃으로 배치해줘" },
  { label: "❌ 삭제", prompt: "선택한 컴포넌트를 삭제해줘" },
];

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
  screenSchema,
  availableHandlers = [],
  statePaths = [],
}: CopilotPanelProps) {
  const editorState = useEditorState();
  const [inputValue, setInputValue] = useState("");
  const [patchText, setPatchText] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [aiResponse, setAiResponse] = useState<CopilotResponse | null>(null);
  
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

  const handleGenerateProposal = async () => {
    if (!inputValue.trim()) {
      return;
    }
    
    setIsGenerating(true);
    setLocalError(null);
    setAiResponse(null);
    
    try {
      // Call the AI backend API
      const response = await fetch("/ai/screen-copilot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          screen_schema: screenSchema,
          prompt: inputValue.trim(),
          selected_component: selectedComponentId,
          context: {
            available_handlers: availableHandlers,
            state_paths: statePaths,
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
      }

      const envelope = await response.json();
      const data = envelope.data as CopilotResponse;

      // Store the AI response
      setAiResponse(data);
      
      // Update the patch text
      if (data.patch && data.patch.length > 0) {
        setPatchText(JSON.stringify(data.patch, null, 2));
      } else {
        setPatchText("[]");
        if (data.suggestions && data.suggestions.length > 0) {
          setLocalError(data.suggestions.join("\n"));
        }
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      setLocalError(`Failed to generate: ${errorMsg}`);
      setPatchText(JSON.stringify({ patch: [], context: contextPayload }, null, 2));
    } finally {
      setIsGenerating(false);
    }
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
    setAiResponse(null);
    editorState.discardProposal();
  };

  const previewStatusLabel = previewEnabled ? "Preview ON" : "Preview OFF";
  const visibleError = localError || editorState.previewError;

  return (
    <div className="flex h-full flex-col border-l transition-all duration-200" data-testid="copilot-panel">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <p className="draft-panel-label">Copilot</p>
          <p className="text-xs">AI-powered screen editing</p>
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

        {/* Quick Action Buttons */}
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">빠른 액션:</p>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.prompt}
                onClick={() => setInputValue(action.prompt)}
                className="px-2 py-1 text-xs rounded-full border border-border hover:border-primary hover:bg-primary/10 transition-colors"
                disabled={isGenerating}
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>

        <textarea
          aria-label="Copilot prompt"
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          placeholder="Describe what you want to change... (e.g., 'Add a submit button', 'Change the table columns')"
          className="h-24 w-full rounded-2xl border px-3 py-2 text-sm outline-none transition focus:border-sky-500"
          disabled={isGenerating}
        />

        <button
          onClick={handleGenerateProposal}
          disabled={!inputValue.trim() || isGenerating}
          className="w-full rounded-2xl bg-sky-600 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-white transition hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isGenerating ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Generating...
            </span>
          ) : (
            "Generate with AI"
          )}
        </button>

        {/* AI Response Display */}
        {aiResponse && (
          <div className="space-y-2">
            {aiResponse.explanation && (
              <div className="rounded-lg bg-emerald-950/30 border border-emerald-800 p-3">
                <p className="text-xs font-medium text-emerald-400">AI Explanation</p>
                <p className="text-xs text-emerald-300 mt-1">{aiResponse.explanation}</p>
              </div>
            )}
            {aiResponse.confidence > 0 && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-400">Confidence:</span>
                <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all ${
                      aiResponse.confidence >= 0.8 ? "bg-emerald-500" :
                      aiResponse.confidence >= 0.5 ? "bg-amber-500" : "bg-red-500"
                    }`}
                    style={{ width: `${aiResponse.confidence * 100}%` }}
                  />
                </div>
                <span className="text-gray-300">{Math.round(aiResponse.confidence * 100)}%</span>
              </div>
            )}
            {aiResponse.suggestions && aiResponse.suggestions.length > 0 && (
              <div className="text-xs text-gray-400">
                <p className="font-medium">Suggestions:</p>
                <ul className="list-disc list-inside mt-1">
                  {aiResponse.suggestions.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="draft-panel-section">
          <p className="draft-panel-label">Patch output (RFC6902)</p>
          <p className="text-xs mt-2">
            JSON Patch array generated by AI, or edit manually.
          </p>
          <Textarea
            value={patchText}
            onChange={(event) => {
              setPatchText(event.target.value);
              setLocalError(null);
            }}
            placeholder='AI will generate patch here, or paste manually...'
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
          disabled={!parseResult.patch && !patchText}
        >
          {previewEnabled ? "Hide Preview" : "Preview Patch"}
        </button>
        <button
          onClick={handleApply}
          className="draft-panel-button w-full bg-emerald-600 hover:bg-emerald-500 text-white"
          disabled={!parseResult.patch}
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