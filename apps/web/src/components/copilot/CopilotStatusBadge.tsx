"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface CopilotStatusBadgeProps {
  confidence: number;
  showLabel?: boolean;
  size?: "sm" | "md";
}

export function CopilotStatusBadge({
  confidence,
  showLabel = true,
  size = "md",
}: CopilotStatusBadgeProps) {
  const percentage = Math.round(confidence * 100);

  let colorClass: string;
  let label: string;

  if (confidence >= 0.8) {
    colorClass = "bg-emerald-500/20 text-emerald-400 border-emerald-500/40";
    label = "High";
  } else if (confidence >= 0.5) {
    colorClass = "bg-amber-500/20 text-amber-400 border-amber-500/40";
    label = "Medium";
  } else {
    colorClass = "bg-red-500/20 text-red-400 border-red-500/40";
    label = "Low";
  }

  const sizeClass = size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border",
        colorClass,
        sizeClass
      )}
    >
      {showLabel && <span>{label}</span>}
      <span className="font-mono font-medium">{percentage}%</span>
    </span>
  );
}
