"use client";

import React, { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import VisualEditor from "./visual/VisualEditor";
import JsonEditor from "./json/JsonEditor";
import PreviewTab from "./preview/PreviewTab";

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
        <TabsTrigger value="preview" data-testid="tab-preview">
          Preview
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
          value="preview"
          className="h-full"
          data-testid="preview-content"
        >
          <PreviewTab />
        </TabsContent>
      </div>
    </Tabs>
  );
}
