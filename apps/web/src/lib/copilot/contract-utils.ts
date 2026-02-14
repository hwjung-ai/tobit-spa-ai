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
    return {
      ok: false,
      reason: `❌ JSON 파싱 실패: 유효한 JSON을 찾을 수 없습니다. 응답 내 유효한 JSON 객체를 반환해주세요. (${contract} 타입 필요)`
    };
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
      : {
        ok: false,
        reason: `❌ 잘못된 screen_patch 형식: JSON Patch 배열 또는 {"patch": [...]} 구조가 필요합니다 (RFC 6902 표준 준수)`
      };
  }

  const expectedType = contract;
  const hasTypedObject = parsed.some((value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    return (value as { type?: unknown }).type === expectedType;
  });

  if (hasTypedObject) return { ok: true, reason: null };

  // Provide more helpful error message with context
  const foundTypes = parsed
    .filter(v => v && typeof v === "object" && !Array.isArray(v))
    .map(v => (v as { type?: unknown }).type)
    .filter(Boolean);

  const typeInfo = foundTypes.length > 0
    ? `발견된 type: [${foundTypes.join(", ")}]`
    : "type 필드를 찾을 수 없습니다";

  return {
    ok: false,
    reason: `❌ 계약 위반: {"type": "${expectedType}"} 형식의 JSON 객체가 필요합니다. ${typeInfo}`
  };
};

export const buildRepairPrompt = (params: {
  contract: CopilotContract;
  originalUserPrompt: string;
  previousAssistantResponse: string;
}) => {
  const contractGuide =
    params.contract === "screen_patch"
      ? "Return ONLY valid JSON Patch operations (RFC 6902). Format: {\"patch\": [{\"op\": \"add\", \"path\": \"/...\", \"value\": ...}, ...]} or just the patch array."
      : `Return ONLY one JSON object with type="${params.contract}". Example: {"type": "${params.contract}", ...}`;

  return [
    "⚠️ CRITICAL: Your previous response violated the output contract. Please fix it.",
    "",
    "REQUIREMENTS:",
    contractGuide,
    "- Return ONLY pure JSON, no markdown, no code fences, no explanations",
    "- Ensure all required fields are included",
    "- Do not add any text before or after the JSON",
    "",
    `Original user request: ${params.originalUserPrompt}`,
    "",
    "Your previous response (invalid):",
    params.previousAssistantResponse,
    "",
    "Please respond with ONLY valid JSON now:"
  ].join("\n");
};
