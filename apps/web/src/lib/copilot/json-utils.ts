export const stripCodeFences = (value: string) => {
  const match = value.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (match && match[1]) return match[1].trim();
  return value.trim();
};

export const tryParseJson = (text: string): unknown | null => {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
};

const extractBalancedJsonFrom = (text: string, startIdx: number) => {
  const startChar = text[startIdx];
  if (startChar !== "{" && startChar !== "[") {
    throw new Error("JSON start token not found");
  }

  const endChar = startChar === "{" ? "}" : "]";
  let depth = 0;
  let inString = false;
  let escape = false;

  for (let i = startIdx; i < text.length; i += 1) {
    const char = text[i];

    if (escape) {
      escape = false;
      continue;
    }
    if (char === "\\") {
      escape = true;
      continue;
    }
    if (char === "\"") {
      inString = !inString;
      continue;
    }
    if (inString) continue;

    if (char === startChar) depth += 1;
    if (char === endChar) {
      depth -= 1;
      if (depth === 0) {
        return text.slice(startIdx, i + 1);
      }
    }
  }

  if (depth > 0 && !inString) {
    return text.slice(startIdx) + endChar.repeat(depth);
  }

  throw new Error("Failed to extract balanced JSON");
};

export const extractJsonCandidates = (text: string) => {
  const candidates: string[] = [];
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (char !== "{" && char !== "[") continue;
    try {
      const candidate = extractBalancedJsonFrom(text, i);
      if (candidate.trim()) candidates.push(candidate);
      i += Math.max(0, candidate.length - 1);
    } catch {
      // ignore invalid start token
    }
  }
  return candidates;
};
