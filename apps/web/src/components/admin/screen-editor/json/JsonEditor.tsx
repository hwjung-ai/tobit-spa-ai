"use client";

import React, { useState } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

export default function JsonEditor() {
  const editorState = useEditorState();
  const [jsonText, setJsonText] = useState(() => {
    if (editorState.screen) {
      return JSON.stringify(editorState.screen, null, 2);
    }
    return "";
  });
  const [localErrors, setLocalErrors] = useState<string[]>([]);

  const handleJsonChange = (text: string) => {
    setJsonText(text);
    setLocalErrors([]);

    // Try to parse and validate
    try {
      JSON.parse(text);
    } catch (err) {
      setLocalErrors([`Invalid JSON: ${err instanceof Error ? err.message : "Unknown error"}`]);
    }
  };

  const handleApplyJson = () => {
    try {
      editorState.updateScreenFromJson(jsonText);
      setLocalErrors([]);
    } catch (err) {
      setLocalErrors([`Parse error: ${err instanceof Error ? err.message : "Unknown error"}`]);
    }
  };

  const handleFormat = () => {
    try {
      const parsed = JSON.parse(jsonText);
      setJsonText(JSON.stringify(parsed, null, 2));
      setLocalErrors([]);
    } catch (err) {
      setLocalErrors([`Cannot format: ${err instanceof Error ? err.message : "Unknown error"}`]);
    }
  };

  const hasJsonErrors = localErrors.length > 0 || editorState.validationErrors.some(e => e.path === "json");

  return (
    <div className="h-full flex flex-col gap-4" data-testid="json-editor">
      {/* Errors */}
      {(localErrors.length > 0 || hasJsonErrors) && (
        <div className="rounded-lg border border-red-800 bg-red-950/50 p-3">
          <p className="text-xs font-semibold text-red-300 mb-2">Errors:</p>
          <div className="space-y-1">
            {localErrors.map((err, idx) => (
              <p key={idx} className="text-xs text-red-400">{err}</p>
            ))}
            {editorState.validationErrors
              .filter(e => e.severity === "error")
              .map((err, idx) => (
                <p key={`validation-${idx}`} className="text-xs text-red-400">
                  {err.path}: {err.message}
                </p>
              ))}
          </div>
        </div>
      )}

      {/* Editor */}
      <Textarea
        value={jsonText}
        onChange={e => handleJsonChange(e.target.value)}
        placeholder="Enter screen schema JSON here..."
        className={`flex-1 font-mono text-xs bg-slate-800 border-slate-700 resize-none ${
          hasJsonErrors ? "border-red-600" : ""
        }`}
        data-testid="json-textarea"
      />

      {/* Actions */}
      <div className="flex gap-2">
        <Button
          onClick={handleFormat}
          variant="outline"
          size="sm"
          data-testid="btn-format-json"
        >
          Format
        </Button>

        <Button
          onClick={handleApplyJson}
          disabled={localErrors.length > 0}
          size="sm"
          className="bg-sky-600 hover:bg-sky-700"
          data-testid="btn-apply-json"
        >
          Apply to Visual
        </Button>
      </div>
    </div>
  );
}
