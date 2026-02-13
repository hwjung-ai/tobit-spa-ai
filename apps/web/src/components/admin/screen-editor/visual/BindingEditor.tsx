"use client";

import React, { useState, useMemo } from "react";
import { PathPicker, type PathTreeNode } from "@/components/admin/screen-editor/common/PathPicker";

export type { PathTreeNode };
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { validateBindingPath } from "@/lib/ui-screen/validation-utils";
import { parseBindingExpression } from "@/lib/ui-screen/binding-path-utils";

interface BindingEditorProps {
  value?: string;
  onChange: (value: string) => void;
  mode?: "binding" | "static";
  onModeChange?: (mode: "binding" | "static") => void;
  stateTree?: PathTreeNode[];
  contextTree?: PathTreeNode[];
  inputsTree?: PathTreeNode[];
  supportedSources?: string[];
  placeholder?: string;
  className?: string;
  showModeToggle?: boolean;
}
export const BindingEditor = React.forwardRef<HTMLDivElement, BindingEditorProps>(
  (
    {
      value = "",
      onChange,
      mode = "binding",
      onModeChange,
      stateTree = [],
      contextTree = [],
      inputsTree = [],
      supportedSources,
      placeholder,
      className = "",
      showModeToggle = true,
    },
    ref
  ) => {
    const [localMode, setLocalMode] = useState<"binding" | "static">(mode);
    const safeValue = typeof value === "string" ? value : "";

    // Initialize static value when switching to static mode
    const handleModeChange = (newMode: "binding" | "static") => {
      setLocalMode(newMode);
      if (onModeChange) {
        onModeChange(newMode);
      }

      // When switching to static mode, clear binding expressions
      if (newMode === "static" && safeValue.startsWith("{{")) {
        const parsed = parseBindingExpression(safeValue);
        if (parsed) {
          onChange("");
        }
      }
    };

    // Validate binding path
    const validationError = useMemo(() => {
      if (localMode !== "binding" || !safeValue) return "";
      const errors = validateBindingPath(safeValue);
      return errors.length > 0 ? errors[0].message : "";
    }, [safeValue, localMode]);

    // Determine which trees to show based on supportedSources
    const filteredStatePaths = supportedSources?.includes("state") !== false ? stateTree : [];
    const filteredContextPaths = supportedSources?.includes("context") !== false ? contextTree : [];
    const filteredInputsPaths = supportedSources?.includes("inputs") !== false ? inputsTree : [];

    return (
      <div ref={ref} className={`space-y-3 ${className}`}>
        {showModeToggle && (
          <Tabs value={localMode} onValueChange={(val) => handleModeChange(val as "binding" | "static")}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger
                className="data-[state=active]:!bg-sky-600 data-[state=active]:!text-white hover:text-foreground-secondary"

                value="binding"
              >
                Binding
              </TabsTrigger>
              <TabsTrigger
                className="data-[state=active]:!bg-sky-600 data-[state=active]:!text-white hover:text-foreground-secondary"

                value="static"
              >
                Static
              </TabsTrigger>
            </TabsList>

            <TabsContent value="binding" className="space-y-2">
              <PathPicker
                value={safeValue}
                onChange={onChange}
                stateTree={filteredStatePaths}
                contextTree={filteredContextPaths}
                inputsTree={filteredInputsPaths}
                placeholder={placeholder || "Select a binding path..."}
                error={validationError}
              />
              <p className="text-xs">
                Select from state, context, inputs, or use trace_id
              </p>
            </TabsContent>

            <TabsContent value="static" className="space-y-2">
              <Input
                value={localMode === "static" ? safeValue : ""}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder || "Enter a static value..."}
              />
              <p className="text-xs">
                Enter a literal value (string, number, etc.)
              </p>
            </TabsContent>
          </Tabs>
        )}

        {!showModeToggle && localMode === "binding" && (
          <PathPicker
            value={safeValue}
            onChange={onChange}
            stateTree={filteredStatePaths}
            contextTree={filteredContextPaths}
            inputsTree={filteredInputsPaths}
            placeholder={placeholder || "Select a binding path..."}
            error={validationError}
          />
        )}

        {!showModeToggle && localMode === "static" && (
          <Input
            value={safeValue}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder || "Enter a static value..."}
          />
        )}
      </div>
    );
  }
);

BindingEditor.displayName = "BindingEditor";
