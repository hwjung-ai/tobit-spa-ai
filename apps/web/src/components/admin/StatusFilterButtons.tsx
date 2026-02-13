"use client";

import { cn } from "@/lib/utils";

type StatusFilterValue = "all" | "draft" | "published";

interface StatusFilterButtonsProps {
  value: StatusFilterValue;
  onChange: (value: StatusFilterValue) => void;
  labelClassName?: string;
  className?: string;
}

const statusBtnClass = (active: boolean) =>
  cn(
    "panel-tab normal-case rounded-md h-7 px-2.5",
    active ? "panel-tab-active" : "panel-tab-inactive",
  );

export default function StatusFilterButtons({
  value,
  onChange,
  labelClassName,
  className,
}: StatusFilterButtonsProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span
        className={cn(
          "text-label-sm normal-case whitespace-nowrap",
          labelClassName,
        )}
      >
        Status
      </span>
      <button onClick={() => onChange("all")} className={statusBtnClass(value === "all")}>
        All
      </button>
      <button onClick={() => onChange("draft")} className={statusBtnClass(value === "draft")}>
        Draft
      </button>
      <button
        onClick={() => onChange("published")}
        className={statusBtnClass(value === "published")}
      >
        Published
      </button>
    </div>
  );
}
