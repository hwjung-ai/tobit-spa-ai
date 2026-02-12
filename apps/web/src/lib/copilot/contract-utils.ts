import { extractJsonCandidates, stripCodeFences, tryParseJson } from "./json-utils";

export type CopilotContract =
  | "api_draft"
  | "cep_draft"
  | "screen_patch"
  | "sim_draft";

export interface ContractValidationResult {
  ok: boolean;
  reason: string | null;
}

const parseCandidateObjects = (text: string): unknown[] => {
  const candidates = [stripCodeFences(text), text];
  const parsed: unknown[] = [];

  for (const candidate of candidates) {
    if (!candidate.trim()) continue;
    const direct = tryParseJson(candidate);
    if (direct !== null) {
      parsed.push(direct);
    }
    for (const extracted of extractJsonCandidates(candidate)) {
      const value = tryParseJson(extracted);
      if (value !== null) {
        parsed.push(value);
      }
    }
  }

  return parsed;
};

export const validateCopilotContract = (
  contract: CopilotContract | undefined,
  text: string
): ContractValidationResult => {
  if (!contract) return { ok: true, reason: null };

  const parsed = parseCandidateObjects(text);
  if (parsed.length === 0) {
    return { ok: false, reason: "JSON payload를 추출하지 못했습니다." };
  }

  if (contract === "screen_patch") {
    const hasPatch = parsed.some((value) => {
      if (Array.isArray(value)) return true;
      return (
        value &&
        typeof value === "object" &&
        Array.isArray((value as { patch?: unknown }).patch)
      );
    });
    return hasPatch
      ? { ok: true, reason: null }
      : { ok: false, reason: "JSON Patch 배열 또는 patch 필드가 필요합니다." };
  }

  const expectedType = contract;
  const hasTypedObject = parsed.some((value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    return (value as { type?: unknown }).type === expectedType;
  });

  if (hasTypedObject) return { ok: true, reason: null };

  return { ok: false, reason: `type=${expectedType} 객체가 필요합니다.` };
};

export const buildRepairPrompt = (params: {
  contract: CopilotContract;
  originalUserPrompt: string;
  previousAssistantResponse: string;
}) => {
  const contractGuide =
    params.contract === "screen_patch"
      ? "Return ONLY valid JSON patch array (RFC 6902) or {\"patch\": [...]}."
      : `Return ONLY one JSON object with type="${params.contract}".`;

  return [
    "Reformat your previous answer to satisfy the output contract.",
    contractGuide,
    "No markdown, no explanation, no code fences.",
    "",
    `Original user request: ${params.originalUserPrompt}`,
    "",
    "Previous invalid response:",
    params.previousAssistantResponse,
  ].join("\n");
};
