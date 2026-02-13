"use client";

import { ScreenDiff, DiffItem } from "@/lib/ui-screen/screen-diff-utils";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Plus, Minus, Edit, Check } from "lucide-react";

interface DiffViewerProps {
  diff: ScreenDiff;
}

function getChangeTypeColor(changeType: string): string {
  switch (changeType) {
    case "added":
      return "bg-green-950/30 border-l-4 border-green-500";
    case "removed":
      return "bg-red-950/30 border-l-4 border-red-500";
    case "modified":
      return "bg-amber-950/30 border-l-4 border-amber-500";
    case "unchanged":
      return "bg-surface-base border-l-4 border-variant";
    default:
      return "bg-surface-base";
  }
}

function getChangeTypeIcon(changeType: string) {
  switch (changeType) {
    case "added":
      return <Plus className="w-4 h-4 text-green-400" />;
    case "removed":
      return <Minus className="w-4 h-4 text-red-400" />;
    case "modified":
      return <Edit className="w-4 h-4 text-amber-400" />;
    case "unchanged":
      return <Check className="w-4 h-4 0" />;
    default:
      return null;
  }
}

function DiffItemRenderer({ item }: { item: DiffItem }) {
  const { changeType, path, before, after, changes } = item;

  return (
    <div className={`p-3 rounded ${getChangeTypeColor(changeType)}`}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">{getChangeTypeIcon(changeType)}</div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-mono break-all">{path}</div>

          {before && !after && (
            <div className="mt-2 text-xs font-mono text-red-300 p-2 rounded overflow-auto border border-red-900/50">
              {JSON.stringify((before as Record<string, unknown>), null, 2)}
            </div>
          )}

          {after && !before && (
            <div className="mt-2 text-xs font-mono text-green-300 p-2 rounded overflow-auto border border-green-900/50">
              {JSON.stringify((after as Record<string, unknown>), null, 2)}
            </div>
          )}

          {changes && (
            <div className="mt-2 space-y-1">
              {Object.entries(changes).map(([key, change]: [string, { before: unknown, after: unknown }]) => (
                <div key={key} className="text-xs">
                  <span className="font-mono">{key}:</span>
                  <span className="ml-2 line-through text-red-400 opacity-70">
                    {JSON.stringify(change.before, null, 2)}
                  </span>
                  <span className="ml-2 text-green-400">
                    → {JSON.stringify(change.after, null, 2)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function DiffViewer({ diff }: DiffViewerProps) {
  const { components, actions, bindings, state } = diff;

  const sections = [
    {
      title: "Components",
      count: components.length,
      items: components,
      defaultOpen: components.some((c) => c.changeType !== "unchanged"),
    },
    {
      title: "Actions",
      count: actions.length,
      items: actions,
      defaultOpen: actions.some((a) => a.changeType !== "unchanged"),
    },
    {
      title: "Bindings",
      count: bindings.length,
      items: bindings,
      defaultOpen: bindings.some((b) => b.changeType !== "unchanged"),
    },
    {
      title: "State Schema",
      count: state.length,
      items: state,
      defaultOpen: state.some((s) => s.changeType !== "unchanged"),
    },
  ];

  return (
    <div className="flex-1 overflow-auto">
      <Accordion type="multiple" defaultValue={sections.filter((s) => s.defaultOpen).map((s, i) => `section-${i}`)}>
        {sections.map((section, idx) => (
          <AccordionItem key={`section-${idx}`} value={`section-${idx}`} className="border-0">
            <AccordionTrigger className="px-4 py-3 hover: font-medium text-sm">
              <div className="flex items-center gap-2">
                <span>{section.title}</span>
                <span className="text-xs px-2 py-0.5 rounded border">
                  {section.count}
                </span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 py-3 space-y-2">
              {section.items.length === 0 ? (
                <div className="text-sm 0 italic">No items</div>
              ) : (
                section.items.map((item, itemIdx) => (
                  <DiffItemRenderer key={`${section.title}-${itemIdx}`} item={item} />
                ))
              )}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
