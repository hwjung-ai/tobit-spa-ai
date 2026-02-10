"use client";

import { useState, useEffect, useMemo } from "react";

/**
 * Catalog item returned by /ops/ui-actions/catalog endpoint.
 * Represents either a built-in action handler or an API Manager API.
 */
export interface CatalogItem {
  action_id: string;
  label?: string;
  description?: string;
  source?: "builtin" | "api_manager";
  mode?: string;
  output?: { state_patch_keys?: string[] };
  required_context?: string[];
  input_schema?: {
    type?: string;
    required?: string[];
    properties?: Record<
      string,
      { type?: string; title?: string; default?: unknown; format?: string }
    >;
  };
  sample_output?: Record<string, unknown> | null;
  tags?: string[];
  /** For API Manager items: additional metadata */
  api_manager_meta?: {
    api_id: string;
    method: string;
    path: string;
    mode: string;
  };
}

export interface HandlerOption {
  value: string;
  label: string;
  source: "builtin" | "api_manager";
}

const FALLBACK_HANDLERS: HandlerOption[] = [
  { value: "fetch_device_detail", label: "Fetch Device Detail", source: "builtin" },
  { value: "list_maintenance_filtered", label: "List Maintenance Filtered", source: "builtin" },
  { value: "create_maintenance_ticket", label: "Create Maintenance Ticket", source: "builtin" },
  { value: "open_maintenance_modal", label: "Open Maintenance Modal", source: "builtin" },
  { value: "close_maintenance_modal", label: "Close Maintenance Modal", source: "builtin" },
];

/**
 * Shared hook for loading the action catalog from backend.
 *
 * Returns the full catalog items, a loading state, an error message (if any),
 * and handler options formatted for Select components.
 *
 * @param enabled - Whether to fetch the catalog. Set to `false` to skip loading.
 */
export function useActionCatalog(enabled: boolean) {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;

    const loadCatalog = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await fetch(
          "/ops/ui-actions/catalog?include_api_manager=true"
        );
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const envelope = await response.json();
        const actions: CatalogItem[] = envelope?.data?.actions ?? [];

        if (!cancelled) {
          if (Array.isArray(actions) && actions.length > 0) {
            setItems(actions);
          } else {
            setError("Catalog returned empty");
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load catalog"
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadCatalog();

    return () => {
      cancelled = true;
    };
  }, [enabled]);

  const handlerOptions: HandlerOption[] = useMemo(() => {
    if (items.length === 0) {
      return FALLBACK_HANDLERS;
    }
    return items.map((item) => ({
      value: item.action_id,
      label: item.label || item.action_id,
      source: (item.source ?? "builtin") as "builtin" | "api_manager",
    }));
  }, [items]);

  const builtinOptions = useMemo(
    () => handlerOptions.filter((h) => h.source === "builtin"),
    [handlerOptions]
  );

  const apiManagerOptions = useMemo(
    () => handlerOptions.filter((h) => h.source === "api_manager"),
    [handlerOptions]
  );

  /**
   * Find catalog item by action_id (handler value).
   */
  const findItem = (handlerValue: string): CatalogItem | null => {
    return items.find((item) => item.action_id === handlerValue) ?? null;
  };

  return {
    items,
    isLoading,
    error,
    handlerOptions,
    builtinOptions,
    apiManagerOptions,
    findItem,
  };
}
