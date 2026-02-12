"use client";

import React, { useMemo } from "react";
import { Component } from "@/lib/ui-screen/screen.schema";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface TreeNode {
  component: Component;
  depth: number;
  parentId?: string;
  index: number;
  siblingCount: number;
  children: TreeNode[];
}

function buildTree(components: Component[], depth = 0, parentId?: string): TreeNode[] {
  if (!components || components.length === 0) return [];

  return components.map((component, index) => ({
    component,
    depth,
    parentId,
    index,
    siblingCount: components.length,
    children: buildTree(
      (component.props?.components as Component[] | undefined) || [],
      depth + 1,
      component.id
    ),
  }));
}

function collectNodeInfo(map: Map<string, TreeNode>, nodes: TreeNode[]) {
  nodes.forEach((node) => {
    map.set(node.component.id, node);
    if (node.children.length > 0) {
      collectNodeInfo(map, node.children);
    }
  });
}

export default function ComponentTreeView() {
  const editorState = useEditorState();
  const { selectedComponentId, moveComponent, selectComponent, screen } = editorState;

  const tree = useMemo(() => {
    if (!screen?.components) return [];
    return buildTree(screen.components);
  }, [screen]);

  const nodeLookup = useMemo(() => {
    const map = new Map<string, TreeNode>();
    collectNodeInfo(map, tree);
    return map;
  }, [tree]);

  const selectedNode = selectedComponentId ? nodeLookup.get(selectedComponentId) : undefined;
  const parentNode = selectedNode?.parentId ? nodeLookup.get(selectedNode.parentId) : undefined;

  const renderTree = (nodes: TreeNode[]) => {
    return nodes.map((node) => {
      const isSelected = node.component.id === selectedComponentId;
      return (
        <div
          key={node.component.id}
          className={cn(
            "rounded-md border px-2 py-2 transition-colors",
            isSelected
              ? "border-sky-500 bg-sky-950/30"
              : "border-transparent hover:border-[var(--border)] bg-[var(--surface-base)]/60"
          )}
          style={{marginLeft: `${node.depth * 12}px`}}
        >
          <div
            className="flex items-center justify-between gap-2 cursor-pointer"
            onClick={() => selectComponent(node.component.id)}
          >
            <div>
              <p className="text-xs font-semibold truncate" style={{color: "var(--foreground)"}}>
                {node.component.label || node.component.id}
              </p>
              <p className="text-[10px] font-mono" style={{color: "var(--muted-foreground)"}}>
                {node.component.type}
              </p>
            </div>
            <div className="flex gap-1">
              <Button
                size="sm"
                className="text-[10px] px-2 h-7 hover: hover:" style={{backgroundColor: "var(--surface-elevated)", color: "var(--foreground-secondary)", borderColor: "var(--border)"}}
                onClick={(e) => {
                  e.stopPropagation();
                  moveComponent(node.component.id, "up");
                }}
                disabled={node.index === 0 || !!node.parentId}
                data-testid={`tree-move-up-${node.component.id}`}
              >
                ▲
              </Button>
              <Button
                size="sm"
                className="text-[10px] px-2 h-7 hover: hover:" style={{backgroundColor: "var(--surface-elevated)", color: "var(--foreground-secondary)", borderColor: "var(--border)"}}
                onClick={(e) => {
                  e.stopPropagation();
                  moveComponent(node.component.id, "down");
                }}
                disabled={node.index === node.siblingCount - 1 || !!node.parentId}
                data-testid={`tree-move-down-${node.component.id}`}
              >
                ▼
              </Button>
            </div>
          </div>

          {node.children.length > 0 && (
            <div className="mt-2 space-y-1">
              {renderTree(node.children)}
            </div>
          )}
        </div>
      );
    });
  };

  const selectedSummary = selectedComponentId && selectedNode ? (
    <div className="space-y-1 border-b pb-2" style={{borderColor: "var(--border)"}}>
      <p className="text-xs font-semibold" style={{color: "var(--foreground-secondary)"}}>
        {selectedNode.component.label || selectedNode.component.id}
      </p>
      <p className="text-[10px]" style={{color: "var(--muted-foreground)"}}>
        type: {selectedNode.component.type}
      </p>
      <p className="text-[10px]" style={{color: "var(--muted-foreground)"}}>
        bindings: {selectedNode.component.bind ? "Yes" : "No"} · actions: {selectedNode.component.actions?.length ? `${selectedNode.component.actions.length}` : "0"}
      </p>
      <p className="text-[10px] 0" style={{color: "var(--foreground)"}}>
        parent: {parentNode ? parentNode.component.label || parentNode.component.id : "Root"} · index: {selectedNode.index + 1}/{selectedNode.siblingCount}
      </p>
    </div>
  ) : (
    <p className="text-xs 0" style={{color: "var(--foreground)"}}>
      Select a component
    </p>
  );

  if (!screen) {
    return null;
  }

  return (
    <div className="flex flex-col h-full" style={{backgroundColor: "var(--surface-overlay)"}}>
      <div className="border-b p-3" style={{borderColor: "var(--border)"}}>
        <h3 className="text-sm font-semibold" style={{color: "var(--foreground-secondary)"}}>
          Component Tree
        </h3>
        <p className="text-xs mt-1" style={{color: "var(--muted-foreground)"}}>
          Hierarchy & selection
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <div className="text-[10px] uppercase tracking-[0.4em] 0" style={{color: "var(--foreground)"}}>
          Selection
        </div>
        {selectedSummary}

        <div className="text-[10px] uppercase tracking-[0.4em] 0" style={{color: "var(--foreground)"}}>
          Tree
        </div>
        {tree.length === 0 ? (
          <div className="text-xs 0" style={{color: "var(--foreground)"}}>
            No components yet
          </div>
        ) : (
          <div className="flex flex-col space-y-2">
            {renderTree(tree)}
          </div>
        )}
      </div>
    </div>
  );
}
