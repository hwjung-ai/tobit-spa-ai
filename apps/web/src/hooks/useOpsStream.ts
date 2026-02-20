"use client";

import { useCallback, useRef, useState } from "react";
import { getAuthHeaders } from "@/lib/apiClient";

/**
 * OPS Stream Request
 */
export interface OpsStreamRequest {
  question: string;
  rerun?: {
    base_plan: Record<string, unknown>;
    patch?: Record<string, unknown>;
    selected_ci_id?: string;
    selected_secondary_ci_id?: string;
  } | null;
  resolver_asset?: string | null;
  schema_asset?: string | null;
  source_asset?: string | null;
  asset_overrides?: Record<string, string> | null;
}

/**
 * SSE Event types for OPS streaming
 */
type OpsSSEEventType =
  | "progress"
  | "tool_start"
  | "tool_complete"
  | "block"
  | "complete"
  | "error";

/**
 * SSE Event handlers
 */
export interface OpsSSEHandlers {
  onProgress?: (event: {
    stage: string;
    message: string;
    elapsed_ms: number;
    completed_stages?: string[];
  }) => void;
  onToolStart?: (event: {
    tool_type: string;
    tool_name: string;
    display_name: string;
    status: string;
  }) => void;
  onToolComplete?: (event: {
    tool_type: string;
    tool_name: string;
    display_name: string;
    status: string;
    elapsed_ms: number;
    result_summary?: string;
  }) => void;
  onBlock?: (event: {
    block: Record<string, unknown>;
    index: number;
    total: number;
    elapsed_ms: number;
  }) => void;
  onComplete?: (event: {
    answer: string;
    blocks: Record<string, unknown>[];
    meta: Record<string, unknown>;
    trace: Record<string, unknown>;
    next_actions: Record<string, unknown>[];
    timing: { total_ms: number };
    completed_stages?: string[];
  }) => void;
  onError?: (event: { message: string; stage: string; elapsed_ms: number }) => void;
}

/**
 * Hook return type
 */
export interface UseOpsStreamReturn {
  isLoading: boolean;
  error: string | null;
  abort: () => void;
  stream: (request: OpsStreamRequest) => Promise<void>;
}

/**
 * Hook for streaming OPS queries with SSE
 *
 * Provides a React hook for connecting to the OPS streaming endpoint
 * and handling real-time progress updates.
 *
 * @example
 * ```tsx
 * const { stream, isLoading, error, abort } = useOpsStream({
 *   onProgress: (e) => console.log(`Stage: ${e.stage}`),
 *   onComplete: (e) => console.log(`Done: ${e.answer}`),
 * });
 *
 * await stream({ question: "Show me servers in production" });
 * ```
 */
export function useOpsStream(handlers: OpsSSEHandlers): UseOpsStreamReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  }, []);

  const stream = useCallback(
    async (request: OpsStreamRequest) => {
      // Abort any existing stream
      abort();

      setIsLoading(true);
      setError(null);

      const abortController = new AbortController();
      abortControllerRef.current = abortController;
      let receivedCompleteEvent = false;
      let streamErrorMessage: string | null = null;
      let currentEventType = "";
      let currentData = "";

      const parseSSEEvent = (eventType: string, data: string) => {
        try {
          const parsed = JSON.parse(data);

          switch (eventType as OpsSSEEventType) {
            case "progress":
              handlers.onProgress?.(parsed);
              break;
            case "tool_start":
              handlers.onToolStart?.(parsed);
              break;
            case "tool_complete":
              handlers.onToolComplete?.(parsed);
              break;
            case "block":
              handlers.onBlock?.(parsed);
              break;
            case "complete":
              receivedCompleteEvent = true;
              handlers.onComplete?.(parsed);
              break;
            case "error":
              streamErrorMessage =
                typeof parsed?.message === "string" ? parsed.message : "SSE stream error";
              handlers.onError?.(parsed);
              break;
            default:
              console.warn(`Unknown SSE event type: ${eventType}`);
          }
        } catch (err) {
          console.error("Failed to parse SSE event:", err);
        }
      };

      try {
        // Build URL - use relative path for Next.js proxy or full URL
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
        const url = baseUrl ? `${baseUrl.replace(/\/+$/, "")}/ops/ask/stream` : "/ops/ask/stream";
        
        const response = await fetch(url, {
          method: "POST",
          headers: {
            ...getAuthHeaders(),
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify(request),
          signal: abortController.signal,
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(
            `HTTP ${response.status}: ${errorText || response.statusText}`
          );
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("Response body is not readable");
        }

        const decoder = new TextDecoder();
        let buffer = "";

        const processLines = (lines: string[]) => {
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEventType = line.slice(7).trim();
              continue;
            }
            if (line.startsWith("data: ")) {
              // Support multi-line SSE data payloads
              const dataLine = line.slice(6);
              currentData = currentData ? `${currentData}\n${dataLine}` : dataLine;
              continue;
            }
            if (line === "") {
              if (currentEventType && currentData) {
                parseSSEEvent(currentEventType, currentData);
              }
              currentEventType = "";
              currentData = "";
            }
          }
        };

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });

          // Process complete lines; keep incomplete tail in buffer
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          processLines(lines);
        }

        // Flush remaining buffered tail and parse last event even without trailing blank line.
        if (buffer) {
          processLines(buffer.split("\n"));
        }
        if (currentEventType && currentData) {
          parseSSEEvent(currentEventType, currentData);
          currentEventType = "";
          currentData = "";
        }

        if (streamErrorMessage) {
          throw new Error(streamErrorMessage);
        }
        if (!receivedCompleteEvent) {
          throw new Error("SSE stream ended before completion event");
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          // User aborted, not an error
          return;
        }

        const errorMessage =
          err instanceof Error ? err.message : "Unknown error occurred";
        setError(errorMessage);
        handlers.onError?.({
          message: errorMessage,
          stage: "unknown",
          elapsed_ms: 0,
        });
      } finally {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    },
    [abort, handlers]
  );

  return {
    isLoading,
    error,
    abort,
    stream,
  };
}
