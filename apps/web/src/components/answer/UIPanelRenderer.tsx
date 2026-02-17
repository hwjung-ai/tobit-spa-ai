"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import type { UIPanelBlock, UIInput, UIAction } from "@/types/uiActions";
import { substituteTemplate } from "@/lib/templateUtils";
import { fetchApi } from "@/lib/adminUtils";
import BlockRenderer from "./BlockRenderer";
import type { AnswerBlock } from "./BlockRenderer";
import Toast from "@/components/admin/Toast";

interface UIPanelRendererProps {
  block: UIPanelBlock;
  traceId: string;
  onResult?: (blocks: AnswerBlock[]) => void;
}

export default function UIPanelRenderer({ block, traceId, onResult }: UIPanelRendererProps) {
  const [inputValues, setInputValues] = useState<Record<string, unknown>>(() => {
    const defaults: Record<string, unknown> = {};
    for (const input of block.inputs) {
      defaults[input.id] = input.default ?? (input.kind === "checkbox" ? false : "");
    }
    return defaults;
  });

  const [resultBlocks, setResultBlocks] = useState<AnswerBlock[]>([]);
  const [actionTraceId, setActionTraceId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "warning" } | null>(null);

  const executeMutation = useMutation({
    mutationFn: async (action: UIAction) => {
      const payload = substituteTemplate(action.payload_template, {
        trace_id: traceId,
        action_id: action.id,
        inputs: inputValues,
      });

      const endpoint = action.endpoint || "/ops/ui-actions";
      const response = await fetchApi<Record<string, unknown>>(endpoint, {
        method: action.method || "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      return response.data as { trace_id?: string; blocks?: AnswerBlock[] };
    },
    onSuccess: (data) => {
      setActionTraceId(data.trace_id || null);
      setResultBlocks(data.blocks || []);
      if (onResult) {
        onResult(data.blocks || []);
      }
    },
  });

  const handleInputChange = (inputId: string, value: unknown) => {
    setInputValues((prev) => ({ ...prev, [inputId]: value }));
  };

  const handleSubmit = (action: UIAction) => {
    // Validate required fields
    const missingRequired = block.inputs
      .filter((input) => input.required && !inputValues[input.id])
      .map((input) => input.label);

    if (missingRequired.length > 0) {
      setToast({ message: `Required fields: ${missingRequired.join(", ")}`, type: "warning" });
      return;
    }

    executeMutation.mutate(action);
  };

  return (
    <div className="container-section border-variant bg-surface-overlay space-y-4">
      {block.title && (
        <h3 className="text-sm font-semibold text-white">{block.title}</h3>
      )}

      {/* Inputs */}
      {block.inputs.length > 0 && (
        <div className="space-y-3">
          {block.inputs.map((input) => (
            <div key={input.id} className="space-y-2">
              <Label htmlFor={input.id} className="text-xs text-muted-foreground">
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
        <div className="mt-3 px-4 py-3 border border-rose-900/50 rounded bg-rose-950/50 text-rose-200">
          {executeMutation.error instanceof Error ? executeMutation.error.message : "Execution failed"}
        </div>
      )}

      {/* Result */}
      {resultBlocks.length > 0 && (
        <div className="mt-4 border-t border-variant pt-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wider text-muted-foreground dark:text-muted-foreground">Result</p>
            {actionTraceId && (
              <a
                href={`/admin/inspector?trace_id=${encodeURIComponent(actionTraceId)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-sky-400 hover:underline"
              >
                Open in Inspector →
              </a>
            )}
          </div>

          {/* Render result blocks inline */}
          <div className="space-y-3">
            <BlockRenderer blocks={resultBlocks} traceId={actionTraceId || ""} />
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />
      )}
    </div>
  );
}

function renderInput(input: UIInput, value: unknown, onChange: (value: unknown) => void) {
  switch (input.kind) {
    case "text":
      return (
        <Input
          id={input.id}
          type="text"
          value={(value as string) || ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={input.placeholder}
          className="border border-variant/50 dark:border-variant/50 text-foreground bg-surface-base dark:bg-surface-base"
        />
      );

    case "number":
      return (
        <Input
          id={input.id}
          type="number"
          value={(value as string | number) || ""}
          onChange={(e) => onChange(parseFloat(e.target.value) || "")}
          placeholder={input.placeholder}
          className="border border-variant/50 dark:border-variant/50 text-foreground bg-surface-base dark:bg-surface-base"
        />
      );

    case "date":
      return (
        <Input
          id={input.id}
          type="date"
          value={(value as string) || ""}
          onChange={(e) => onChange(e.target.value)}
          className="border border-variant/50 dark:border-variant/50 text-foreground bg-surface-base dark:bg-surface-base"
        />
      );

    case "datetime":
      return (
        <Input
          id={input.id}
          type="datetime-local"
          value={(value as string) || ""}
          onChange={(e) => onChange(e.target.value)}
          className="border border-variant/50 dark:border-variant/50 text-foreground bg-surface-base dark:bg-surface-base"
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
        <Select value={(value as string) || ""} onValueChange={onChange}>
          <SelectTrigger className="border border-variant/50 dark:border-variant/50 text-foreground bg-surface-base dark:bg-surface-base">
            <SelectValue placeholder={input.placeholder || "Select..."} />
          </SelectTrigger>
          <SelectContent>
            {input.options?.map((option) => (
              <SelectItem key={String(option.value)} value={String(option.value)}>
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
