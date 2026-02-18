/**
 * useScreenCopilot - Hook for calling the backend screen copilot API
 *
 * This hook integrates with the /ai/screen-copilot endpoint to generate
 * JSON Patch operations for screen modifications using AI.
 */
import { useState, useCallback } from "react";
import { fetchApi } from "@/lib/adminUtils";

interface JsonPatchOperation {
  op: string;
  path: string;
  value?: unknown;
  from?: string;
}

interface ScreenCopilotContext {
  available_handlers?: string[];
  state_paths?: string[];
}

interface ScreenCopilotRequest {
  screen_schema: Record<string, unknown>;
  prompt: string;
  selected_component?: string | null;
  context?: ScreenCopilotContext;
}

interface ScreenCopilotResponse {
  patch: JsonPatchOperation[];
  explanation: string;
  confidence: number;
  suggestions: string[];
}

interface UseScreenCopilotReturn {
  isGenerating: boolean;
  response: ScreenCopilotResponse | null;
  error: string | null;
  generatePatch: (
    screenSchema: Record<string, unknown>,
    prompt: string,
    selectedComponent: string | null,
    availableHandlers: string[],
    statePaths: string[]
  ) => Promise<ScreenCopilotResponse | null>;
  clearResponse: () => void;
}

/**
 * Hook to interact with the backend screen copilot API.
 *
 * @example
 * ```tsx
 * const { isGenerating, response, error, generatePatch } = useScreenCopilot();
 *
 * const handleSubmit = async () => {
 *   const result = await generatePatch(
 *     screenSchema,
 *     "Add a submit button",
 *     selectedComponentId,
 *     availableHandlers,
 *     statePaths
 *   );
 *   if (result) {
 *     // Use result.patch, result.explanation, result.confidence, result.suggestions
 *   }
 * };
 * ```
 */
export function useScreenCopilot(): UseScreenCopilotReturn {
  const [isGenerating, setIsGenerating] = useState(false);
  const [response, setResponse] = useState<ScreenCopilotResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const generatePatch = useCallback(
    async (
      screenSchema: Record<string, unknown>,
      prompt: string,
      selectedComponent: string | null,
      availableHandlers: string[],
      statePaths: string[]
    ): Promise<ScreenCopilotResponse | null> => {
      if (!prompt.trim()) {
        setError("Prompt cannot be empty");
        return null;
      }

      setIsGenerating(true);
      setError(null);
      setResponse(null);

      const requestBody: ScreenCopilotRequest = {
        screen_schema: screenSchema,
        prompt: prompt.trim(),
        selected_component: selectedComponent,
        context: {
          available_handlers: availableHandlers,
          state_paths: statePaths,
        },
      };

      try {
        const envelope = await fetchApi<ScreenCopilotResponse>("/ai/screen-copilot", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(requestBody),
        });

        if (envelope?.data) {
          setResponse(envelope.data);
          return envelope.data;
        }

        throw new Error("No data in response");
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to generate patch";
        setError(message);
        return null;
      } finally {
        setIsGenerating(false);
      }
    },
    []
  );

  const clearResponse = useCallback(() => {
    setResponse(null);
    setError(null);
  }, []);

  return {
    isGenerating,
    response,
    error,
    generatePatch,
    clearResponse,
  };
}

export type {
  JsonPatchOperation,
  ScreenCopilotResponse,
  ScreenCopilotContext,
  UseScreenCopilotReturn,
};
