"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { UIPanelBlock, UIInput, UIAction } from "@/types/uiActions";
import { substituteTemplate } from "@/lib/templateUtils";
import { fetchApi } from "@/lib/adminUtils";
import BlockRenderer from "./BlockRenderer";

interface UIPanelRendererProps {
  block: UIPanelBlock;
  traceId: string;
  onResult?: (blocks: any[]) => void;
}

export default function UIPanelRenderer({ block, traceId, onResult }: UIPanelRendererProps) {
  const [inputValues, setInputValues] = useState<Record<string, any>>(() => {
    const defaults: Record<string, any> = {};
    for (const input of block.inputs) {
      defaults[input.id] = input.default ?? (input.kind === "checkbox" ? false : "");
    }
    return defaults;
  });

  const [resultBlocks, setResultBlocks] = useState<any[]>([]);
  const [actionTraceId, setActionTraceId] = useState<string | null>(null);

  const executeMutation = useMutation({
    mutationFn: async (action: UIAction) => {
      const payload = substituteTemplate(action.payload_template, {
        trace_id: traceId,
        action_id: action.id,
        inputs: inputValues,
      });

      const endpoint = action.endpoint || "/ops/ui-actions";
      const response = await fetchApi<any>(endpoint, {
        method: action.method || "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      return response.data;
    },
    onSuccess: (data) => {
      setActionTraceId(data.trace_id);
      setResultBlocks(data.blocks || []);
      if (onResult) {
        onResult(data.blocks || []);
      }
    },
  });

  const handleInputChange = (inputId: string, value: any) => {
    setInputValues((prev) => ({ ...prev, [inputId]: value }));
  };

  const handleSubmit = (action: UIAction) => {
    // Validate required fields
    const missingRequired = block.inputs
      .filter((input) => input.required && !inputValues[input.id])
      .map((input) => input.label);

    if (missingRequired.length > 0) {
      alert(`Required fields: ${missingRequired.join(", ")}`);
      return;
    }

    executeMutation.mutate(action);
  };

  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-4">
      {block.title && (
        <h3 className="text-sm font-semibold text-white">{block.title}</h3>
      )}

      {/* Inputs */}
      {block.inputs.length > 0 && (
        <div className="space-y-3">
          {block.inputs.map((input) => (
            <div key={input.id} className="space-y-2">
              <Label htmlFor={input.id} className="text-xs text-slate-300">
                {input.label}
                {input.required && <span className="text-rose-400 ml-1">*</span>}
              </Label>
              {renderInput(input, inputValues[input.id], (value) => handleInputChange(input.id, value))}
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      {block.actions.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {block.actions.map((action) => (
            <Button
              key={action.id}
              variant={action.variant || "default"}
              onClick={() => handleSubmit(action)}
              disabled={executeMutation.isPending}
              className="text-xs"
            >
              {executeMutation.isPending ? "Loading..." : action.label}
            </Button>
          ))}
        </div>
      )}

      {/* Error */}
      {executeMutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>
            {executeMutation.error instanceof Error ? executeMutation.error.message : "Execution failed"}
          </AlertDescription>
        </Alert>
      )}

      {/* Result */}
      {resultBlocks.length > 0 && (
        <div className="mt-4 border-t border-slate-700 pt-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Result</p>
            {actionTraceId && (
              <a
                href={`/admin/inspector?trace_id=${encodeURIComponent(actionTraceId)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-400 hover:underline"
              >
                Open in Inspector →
              </a>
            )}
          </div>

          {/* Render result blocks inline */}
          <div className="space-y-3">
            {resultBlocks.map((resultBlock, idx) => (
              <BlockRenderer key={idx} block={resultBlock} index={idx} traceId={actionTraceId || ""} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function renderInput(input: UIInput, value: any, onChange: (value: any) => void) {
  switch (input.kind) {
    case "text":
      return (
        <Input
          id={input.id}
          type="text"
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={input.placeholder}
          className="bg-slate-950/50 border-slate-700 text-white"
        />
      );

    case "number":
      return (
        <Input
          id={input.id}
          type="number"
          value={value || ""}
          onChange={(e) => onChange(parseFloat(e.target.value) || "")}
          placeholder={input.placeholder}
          className="bg-slate-950/50 border-slate-700 text-white"
        />
      );

    case "date":
      return (
        <Input
          id={input.id}
          type="date"
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          className="bg-slate-950/50 border-slate-700 text-white"
        />
      );

    case "datetime":
      return (
        <Input
          id={input.id}
          type="datetime-local"
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          className="bg-slate-950/50 border-slate-700 text-white"
        />
      );

    case "checkbox":
      return (
        <div className="flex items-center space-x-2">
          <Checkbox
            id={input.id}
            checked={!!value}
            onCheckedChange={(checked) => onChange(checked)}
          />
        </div>
      );

    case "select":
      return (
        <Select value={value || ""} onValueChange={onChange}>
          <SelectTrigger className="bg-slate-950/50 border-slate-700 text-white">
            <SelectValue placeholder={input.placeholder || "Select..."} />
          </SelectTrigger>
          <SelectContent>
            {input.options?.map((option) => (
              <SelectItem key={option.value} value={String(option.value)}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );

    default:
      return <span className="text-xs text-rose-400">Unsupported input kind: {input.kind}</span>;
  }
}
