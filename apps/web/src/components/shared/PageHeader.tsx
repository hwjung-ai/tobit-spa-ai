"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * PageHeader - Standard page header component
 *
 * Follows DESIGN_SYSTEM_GUIDE.md Phase 12 standards:
 * - Title: text-2xl font-semibold with proper color
 * - Description: mt-2 text-sm with muted color
 * - Actions: Right-aligned action buttons
 *
 * @example
 * ```tsx
 * <PageHeader
 *   title="Operations"
 *   description="Query CI configuration, metrics, history, and relationships."
 *   actions={<Button>Create New</Button>}
 * />
 * ```
 */
export interface PageHeaderProps {
  /** Page title */
  title: string;
  /** Optional description below the title */
  description?: string;
  /** Optional action buttons on the right side */
  actions?: ReactNode;
  /** Optional className for custom styling */
  className?: string;
}

export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div className={cn("page-header", className)}>
      <div className="page-header-title-group">
        <h1 className="page-header-title">{title}</h1>
        {description && (
          <p className="page-header-description">{description}</p>
        )}
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </div>
  );
}

/**
 * PageHeaderWithDivider - Page header with bottom divider
 *
 * Use this when you want a visual separator below the header.
 */
export interface PageHeaderWithDividerProps extends PageHeaderProps {
  /** Show divider below header (default: true) */
  showDivider?: boolean;
}

export function PageHeaderWithDivider({
  title,
  description,
  actions,
  className,
  showDivider = true,
}: PageHeaderWithDividerProps) {
  return (
    <>
      <PageHeader
        title={title}
        description={description}
        actions={actions}
        className={className}
      />
      {showDivider && <div className="page-header-divider" />}
    </>
  );
}

/**
 * PageHeaderCentered - Centered page header (no actions)
 *
 * Use this for simple pages without action buttons.
 */
export interface PageHeaderCenteredProps {
  /** Page title */
  title: string;
  /** Optional description below the title */
  description?: string;
  /** Optional className for custom styling */
  className?: string;
}

export function PageHeaderCentered({
  title,
  description,
  className,
}: PageHeaderCenteredProps) {
  return (
    <div className={cn("page-header page-header-centered", className)}>
      <div className="page-header-title-group">
        <h1 className="page-header-title">{title}</h1>
        {description && (
          <p className="page-header-description">{description}</p>
        )}
      </div>
    </div>
  );
}
