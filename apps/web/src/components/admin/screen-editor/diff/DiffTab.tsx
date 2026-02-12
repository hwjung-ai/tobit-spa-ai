"use client";

import { useMemo } from "react";
import { compareScreens } from "@/lib/ui-screen/screen-diff-utils";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import DiffControls from "./DiffControls";
import DiffSummary from "./DiffSummary";
import DiffViewer from "./DiffViewer";

export default function DiffTab() {
  const editorState = useEditorState();

  const diff = useMemo(() => {
    const effective = editorState.screen;
    if (!effective) return null;
    return compareScreens(editorState.published, effective);
  }, [editorState.screen, editorState.published]);

  if (!diff) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-sm text-[var(--foreground)]0">No screen loaded</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-[var(--surface-base)] text-[var(--foreground)]">
      <DiffControls />
      <DiffSummary diff={diff} />
      <DiffViewer diff={diff} />
    </div>
  );
}
