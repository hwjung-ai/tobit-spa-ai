"use client";

import React, { useState, useMemo } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ChevronDown } from "lucide-react";

export interface PathTreeNode {
  name: string;
  fullPath: string;
  children?: PathTreeNode[];
  type?: string;
  isLeaf?: boolean;
}

interface PathPickerProps {
  value?: string;
  onChange: (value: string) => void;
  stateTree?: PathTreeNode[];
  contextTree?: PathTreeNode[];
  inputsTree?: PathTreeNode[];
  placeholder?: string;
  className?: string;
  error?: string;
}

/**
 * PathPicker Component
 *
 * Hierarchical path picker for selecting binding expressions from state, context, inputs, or trace_id.
 * Supports both dropdown selection and raw mode for manual path entry.
 *
 * Used by: BindingEditor, PayloadTemplateEditor, VisibilityEditor
 *
 * @param value - Current binding expression (e.g., "{{state.device_id}}")
 * @param onChange - Callback when path is selected
 * @param stateTree - Hierarchical state paths
 * @param contextTree - Hierarchical context paths
 * @param inputsTree - Hierarchical inputs paths
 * @param placeholder - Placeholder text for input field
 * @param className - Additional CSS classes
 * @param error - Error message to display
 */
export const PathPicker = React.forwardRef<HTMLDivElement, PathPickerProps>(
  (
    {
      value = "",
      onChange,
      stateTree = [],
      contextTree = [],
      inputsTree = [],
      placeholder = "Select a path...",
      className = "",
      error,
    },
    ref
  ) => {
    const [isRawMode, setIsRawMode] = useState(false);
    const [rawValue, setRawValue] = useState("");

    // Parse binding expression to extract source and path
    const parsed = useMemo(() => {
      const match = value.match(/^\{\{([\w.]+)\}\}$/);
      if (!match) return { source: "", path: "", isValid: false };

      const parts = match[1].split(".");
      const source = parts[0];
      const path = parts.slice(1).join(".");

      return {
        source,
        path,
        isValid: ["state", "context", "inputs", "trace_id"].includes(source),
      };
    }, [value]);

    // Display label for selected value
    const displayLabel = useMemo(() => {
      if (isRawMode) {
        return "Raw Mode";
      }
      if (parsed.isValid) {
        return `${parsed.source}.${parsed.path}`;
      }
      return placeholder;
    }, [parsed, isRawMode, placeholder]);

    const handleSelectPath = (source: string, path: string) => {
      const newValue = `{{${source}${path ? "." + path : ""}}}`;
      onChange(newValue);
      setIsRawMode(false);
    };

    const handleRawModeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      setRawValue(val);
      onChange(val);
    };

    const toggleRawMode = () => {
      if (!isRawMode) {
        setRawValue(value);
      }
      setIsRawMode(!isRawMode);
    };

    return (
      <div ref={ref} className={`space-y-2 ${className}`}>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            {isRawMode ? (
              <Input
                value={rawValue}
                onChange={handleRawModeChange}
                placeholder="e.g., {{state.device_id}}"
                className={error ? "border-red-500" : ""}
              />
            ) : (
              <DropdownMenu>
                <DropdownMenuContent side="bottom" align="start" className="w-64">
                  {/* State section */}
                  {stateTree.length > 0 && (
                    <>
                      <DropdownMenuSub>
                        <DropdownMenuSubTrigger>
                          <span className="font-semibold">state</span>
                        </DropdownMenuSubTrigger>
                        <DropdownMenuSubContent>
                          <DropdownMenuItem onClick={() => handleSelectPath("state", "")}>
                            <span className="text-xs text-gray-500">(root)</span>
                          </DropdownMenuItem>
                          {renderPathTree(
                            stateTree,
                            "state",
                            handleSelectPath
                          )}
                        </DropdownMenuSubContent>
                      </DropdownMenuSub>
                    </>
                  )}

                  {/* Context section */}
                  {contextTree.length > 0 && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuSub>
                        <DropdownMenuSubTrigger>
                          <span className="font-semibold">context</span>
                        </DropdownMenuSubTrigger>
                        <DropdownMenuSubContent>
                          <DropdownMenuItem onClick={() => handleSelectPath("context", "")}>
                            <span className="text-xs text-gray-500">(root)</span>
                          </DropdownMenuItem>
                          {renderPathTree(
                            contextTree,
                            "context",
                            handleSelectPath
                          )}
                        </DropdownMenuSubContent>
                      </DropdownMenuSub>
                    </>
                  )}

                  {/* Inputs section */}
                  {inputsTree.length > 0 && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuSub>
                        <DropdownMenuSubTrigger>
                          <span className="font-semibold">inputs</span>
                        </DropdownMenuSubTrigger>
                        <DropdownMenuSubContent>
                          <DropdownMenuItem onClick={() => handleSelectPath("inputs", "")}>
                            <span className="text-xs text-gray-500">(root)</span>
                          </DropdownMenuItem>
                          {renderPathTree(
                            inputsTree,
                            "inputs",
                            handleSelectPath
                          )}
                        </DropdownMenuSubContent>
                      </DropdownMenuSub>
                    </>
                  )}

                  {/* trace_id */}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => handleSelectPath("trace_id", "")}>
                    <span>trace_id</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>

                <button
                  className={`w-full px-3 py-2 border rounded-md text-sm text-left flex items-center justify-between transition-colors ${
                    error
                      ? "border-red-500 bg-red-50"
                      : "border-gray-300 bg-white hover:bg-gray-50"
                  }`}
                >
                  <span className="text-gray-700">{displayLabel}</span>
                  <ChevronDown className="w-4 h-4 text-gray-500" />
                </button>
              </DropdownMenu>
            )}
          </div>

          <Button
            variant={isRawMode ? "default" : "outline"}
            size="sm"
            onClick={toggleRawMode}
            className="px-3"
          >
            {isRawMode ? "Select" : "Raw"}
          </Button>
        </div>

        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    );
  }
);

PathPicker.displayName = "PathPicker";

/**
 * Recursively render path tree as DropdownMenu items and sub-menus
 */
function renderPathTree(
  nodes: PathTreeNode[],
  source: string,
  onSelect: (source: string, path: string) => void,
  parentPath: string = ""
): React.ReactNode {
  return nodes.map((node) => {
    const currentPath = parentPath ? `${parentPath}.${node.name}` : node.name;

    if (node.children && node.children.length > 0) {
      // Parent node with children - render as sub-menu
      return (
        <DropdownMenuSub key={currentPath}>
          <DropdownMenuSubTrigger>
            <span className="text-sm">{node.name}</span>
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent>
            <DropdownMenuItem onClick={() => onSelect(source, currentPath)}>
              <span className="text-xs text-gray-500">(this level)</span>
            </DropdownMenuItem>
            {renderPathTree(node.children, source, onSelect, currentPath)}
          </DropdownMenuSubContent>
        </DropdownMenuSub>
      );
    } else {
      // Leaf node - render as menu item
      return (
        <DropdownMenuItem
          key={currentPath}
          onClick={() => onSelect(source, currentPath)}
        >
          <span className="text-sm">{node.name}</span>
        </DropdownMenuItem>
      );
    }
  });
}
