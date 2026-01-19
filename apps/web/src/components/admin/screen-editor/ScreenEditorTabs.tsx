"use client";

import React, { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import VisualEditor from "./visual/VisualEditor";
import JsonEditor from "./json/JsonEditor";
import BindingTab from "./binding/BindingTab";
import ActionTab from "./actions/ActionTab";
import PreviewTab from "./preview/PreviewTab";
import DiffTab from "./diff/DiffTab";

interface ScreenEditorTabsProps {
  assetId: string;
}

export default function ScreenEditorTabs({ assetId }: ScreenEditorTabsProps) {
  const [activeTab, setActiveTab] = useState("visual");

  return (
    <Tabs
      value={activeTab}
      onValueChange={setActiveTab}
      className="w-full h-full flex flex-col"
      data-testid="editor-tabs"
    >
      <TabsList className="mx-6 mt-4 bg-slate-800 border-b border-slate-700 rounded-none gap-1">
        <TabsTrigger value="visual" data-testid="tab-visual">
          Visual Editor
        </TabsTrigger>
        <TabsTrigger value="json" data-testid="tab-json">
          JSON
        </TabsTrigger>
        <TabsTrigger value="binding" data-testid="tab-binding">
          Binding
        </TabsTrigger>
        <TabsTrigger value="action" data-testid="tab-action">
          Action
        </TabsTrigger>
        <TabsTrigger value="preview" data-testid="tab-preview">
          Preview
        </TabsTrigger>
        <TabsTrigger value="diff" data-testid="tab-diff">
          Diff
        </TabsTrigger>
      </TabsList>

      <div className="flex-1 overflow-hidden px-6 py-4">
        <TabsContent
          value="visual"
          className="h-full"
          data-testid="visual-editor-content"
        >
          <VisualEditor />
        </TabsContent>

        <TabsContent
          value="json"
          className="h-full"
          data-testid="json-editor-content"
        >
          <JsonEditor />
        </TabsContent>

        <TabsContent
          value="binding"
          className="h-full"
          data-testid="binding-editor-content"
        >
          <BindingTab />
        </TabsContent>

        <TabsContent
          value="action"
          className="h-full"
          data-testid="action-editor-content"
        >
          <ActionTab />
        </TabsContent>

        <TabsContent
          value="preview"
          className="h-full"
          data-testid="preview-content"
        >
          <PreviewTab />
        </TabsContent>

        <TabsContent
          value="diff"
          className="h-full"
          data-testid="diff-content"
        >
          <DiffTab />
        </TabsContent>
      </div>
    </Tabs>
  );
}
