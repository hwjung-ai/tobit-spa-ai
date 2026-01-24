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
      return "bg-green-50 border-l-4 border-green-500";
    case "removed":
      return "bg-red-50 border-l-4 border-red-500";
    case "modified":
      return "bg-amber-50 border-l-4 border-amber-500";
    case "unchanged":
      return "bg-slate-50 border-l-4 border-slate-300";
    default:
      return "bg-white";
  }
}

function getChangeTypeIcon(changeType: string) {
  switch (changeType) {
    case "added":
      return <Plus className="w-4 h-4 text-green-600" />;
    case "removed":
      return <Minus className="w-4 h-4 text-red-600" />;
    case "modified":
      return <Edit className="w-4 h-4 text-amber-600" />;
    case "unchanged":
      return <Check className="w-4 h-4 text-slate-400" />;
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
          <div className="text-sm font-mono text-slate-700 break-all">{path}</div>

          {before && !after && (
            <div className="mt-2 text-xs font-mono bg-red-100 text-red-800 p-2 rounded overflow-auto">
              {JSON.stringify((before as Record<string, unknown>), null, 2)}
            </div>
          )}

          {after && !before && (
            <div className="mt-2 text-xs font-mono bg-green-100 text-green-800 p-2 rounded overflow-auto">
              {JSON.stringify((after as Record<string, unknown>), null, 2)}
            </div>
          )}

          {changes && (
            <div className="mt-2 space-y-1">
              {Object.entries(changes).map(([key, change]: [string, {before: unknown, after: unknown}]) => (
                <div key={key} className="text-xs">
                  <span className="font-mono text-slate-700">{key}:</span>
                  <span className="ml-2 line-through text-red-700">
                    {JSON.stringify(change.before, null, 2)}
                  </span>
                  <span className="ml-2 text-green-700">
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
            <AccordionTrigger className="px-4 py-3 hover:bg-slate-100 font-medium text-sm">
              <div className="flex items-center gap-2">
                <span>{section.title}</span>
                <span className="text-xs bg-slate-200 text-slate-700 px-2 py-0.5 rounded">
                  {section.count}
                </span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 py-3 space-y-2">
              {section.items.length === 0 ? (
                <div className="text-sm text-slate-500 italic">No items</div>
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
