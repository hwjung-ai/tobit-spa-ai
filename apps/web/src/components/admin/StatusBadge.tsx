"use client";

import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string | null | undefined;
  className?: string;
}

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  published: "Published",
  active: "Active",
  inactive: "Inactive",
  pending: "Pending",
  failed: "Failed",
  success: "Success",
};

function toStatusKey(status: string | null | undefined): string {
  return String(status ?? "draft").trim().toLowerCase();
}

export function formatStatusLabel(status: string | null | undefined): string {
  const key = toStatusKey(status);
  return STATUS_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const key = toStatusKey(status);
  const isPositive = key === "published" || key === "active" || key === "success";

  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-md border px-2 text-tiny font-bold uppercase tracking-wider leading-none whitespace-nowrap",
        isPositive
          ? "status-badge-published"
          : "status-badge-draft",
        className,
      )}
    >
      {formatStatusLabel(status)}
    </span>
  );
}
