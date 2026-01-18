"use client";

import React, { useState, useMemo } from "react";
import { PathPicker, type PathTreeNode } from "@/components/admin/screen-editor/common/PathPicker";
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

/**
 * BindingEditor Component
 *
 * Provides UI for editing both binding expressions and static values.
 * Supports toggling between:
 * - Binding mode: Path picker for {{state.x}}, {{context.y}}, etc.
 * - Static mode: Direct value input for static text/numbers
 *
 * Used by: PropertiesPanel (for component props)
 *
 * @param value - Current value (binding or static)
 * @param onChange - Callback when value changes
 * @param mode - Current mode ("binding" or "static")
 * @param onModeChange - Callback when mode changes
 * @param stateTree - Hierarchical state paths
 * @param contextTree - Hierarchical context paths
 * @param inputsTree - Hierarchical inputs paths
 * @param supportedSources - Which sources are supported (default: all)
 * @param placeholder - Placeholder text
 * @param className - Additional CSS classes
 * @param showModeToggle - Show Binding/Static toggle (default: true)
 */
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
    const [staticValue, setStaticValue] = useState("");

    // Initialize static value when switching to static mode
    const handleModeChange = (newMode: "binding" | "static") => {
      setLocalMode(newMode);
      if (onModeChange) {
        onModeChange(newMode);
      }

      // When switching to static mode, extract value if it's currently a binding
      if (newMode === "static" && value.startsWith("{{")) {
        const parsed = parseBindingExpression(value);
        if (parsed) {
          setStaticValue(value);
        }
      } else if (newMode === "static") {
        setStaticValue(value);
      }
    };

    // Validate binding path
    const validationError = useMemo(() => {
      if (localMode !== "binding" || !value) return "";
      const error = validateBindingPath(value, {
        state: stateTree,
        context: contextTree,
        inputs: inputsTree,
      });
      return error ? error.message : "";
    }, [value, localMode, stateTree, contextTree, inputsTree]);

    // Determine which trees to show based on supportedSources
    const filteredStatePaths = supportedSources?.includes("state") !== false ? stateTree : [];
    const filteredContextPaths = supportedSources?.includes("context") !== false ? contextTree : [];
    const filteredInputsPaths = supportedSources?.includes("inputs") !== false ? inputsTree : [];

    return (
      <div ref={ref} className={`space-y-3 ${className}`}>
        {showModeToggle && (
          <Tabs value={localMode} onValueChange={(val) => handleModeChange(val as "binding" | "static")}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="binding">Binding</TabsTrigger>
              <TabsTrigger value="static">Static</TabsTrigger>
            </TabsList>

            <TabsContent value="binding" className="space-y-2">
              <PathPicker
                value={value}
                onChange={onChange}
                stateTree={filteredStatePaths}
                contextTree={filteredContextPaths}
                inputsTree={filteredInputsPaths}
                placeholder={placeholder || "Select a binding path..."}
                error={validationError}
              />
              <p className="text-xs text-gray-500">
                Select from state, context, inputs, or use trace_id
              </p>
            </TabsContent>

            <TabsContent value="static" className="space-y-2">
              <Input
                value={localMode === "static" ? (typeof value === "string" ? value : "") : ""}
                onChange={(e) => {
                  const val = e.target.value;
                  setStaticValue(val);
                  onChange(val);
                }}
                placeholder={placeholder || "Enter a static value..."}
              />
              <p className="text-xs text-gray-500">
                Enter a literal value (string, number, etc.)
              </p>
            </TabsContent>
          </Tabs>
        )}

        {!showModeToggle && localMode === "binding" && (
          <PathPicker
            value={value}
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
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder || "Enter a static value..."}
          />
        )}
      </div>
    );
  }
);

BindingEditor.displayName = "BindingEditor";
