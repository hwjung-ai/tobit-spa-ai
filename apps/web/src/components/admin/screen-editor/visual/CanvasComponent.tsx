"use client";

import React, { useState } from "react";
import { Component } from "@/lib/ui-screen/screen.schema";
import { Button } from "@/components/ui/button";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import ConfirmDialog from "@/components/ui/ConfirmDialog";

interface CanvasComponentProps {
  component: Component;
  isSelected: boolean;
  onSelect: () => void;
}

export default function CanvasComponent({
  component,
  isSelected,
  onSelect,
}: CanvasComponentProps) {
  const editorState = useEditorState();
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <div
      onClick={onSelect}
      className={`p-3 rounded-lg border-2 cursor-pointer transition-colors ${
        isSelected
          ? "border-sky-500 bg-sky-950/30"
          : "border-slate-700 bg-slate-800 hover:bg-slate-700"
      }`}
      data-testid={`canvas-component-${component.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-slate-100 truncate">
            {component.label || component.id}
          </div>
          <div className="text-xs text-slate-400 font-mono">
            {component.type}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            ID: {component.id}
          </div>
        </div>

        {isSelected && (
          <>
            <Button
              size="sm"
              variant="destructive"
              onClick={e => {
                e.stopPropagation();
                setConfirmOpen(true);
              }}
              className="h-7 px-2"
              data-testid={`btn-delete-${component.id}`}
            >
              ✕
            </Button>
            <ConfirmDialog
              open={confirmOpen}
              onOpenChange={setConfirmOpen}
              title="Delete component"
              description={`Are you sure you want to delete ${component.label || component.id}?`}
              confirmLabel="Delete"
              onConfirm={() => {
                editorState.deleteComponent(component.id);
              }}
            />
          </>
        )}
      </div>
    </div>
  );
}
