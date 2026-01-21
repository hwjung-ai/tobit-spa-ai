"""
RCA Hypothesis Summarizer - LLM-based description generation

Uses LLM ONLY for text summarization/explanation, NOT for hypothesis generation.
All hypotheses and evidence are generated deterministically.
"""

from typing import List, Dict, Any, Optional
import logging

from app.llm.client import get_llm_client

logger = logging.getLogger(__name__)


class RCASummarizer:
    """Summarize RCA hypotheses using LLM"""

    def __init__(self):
        self.llm = get_llm_client()
        # Use the default model from LLM client (from CHAT_MODEL environment variable)
        # self.model is no longer needed as llm.create_response uses default_model when model=None

    def summarize_hypotheses(
        self,
        hypotheses: List[Dict[str, Any]],
        max_length: int = 400,  # ~3-6 sentences
        language: str = "korean",
    ) -> List[Dict[str, Any]]:
        """
        Add LLM-generated descriptions to hypotheses.

        Args:
            hypotheses: List of hypothesis dicts with title, evidence, checks, actions
            max_length: Max chars for description
            language: Output language (korean, english)

        Returns:
            Same hypotheses with 'description' field populated
        """
        result = []

        for hyp in hypotheses:
            try:
                description = self._generate_description(
                    hyp["title"],
                    hyp["evidence"],
                    hyp["checks"],
                    hyp["recommended_actions"],
                    max_length,
                    language,
                )
                hyp["description"] = description
            except Exception as e:
                logger.warning(f"Failed to generate description for {hyp['title']}: {e}")
                # Fallback: use evidence snippets as description
                hyp["description"] = self._fallback_description(hyp, language)

            result.append(hyp)

        return result

    def _generate_description(
        self,
        title: str,
        evidence: List[Dict[str, str]],
        checks: List[str],
        recommended_actions: List[str],
        max_length: int,
        language: str,
    ) -> str:
        """Generate description via LLM for a single hypothesis"""

        # Build evidence snippet for context
        evidence_str = "\n".join(
            [f"- Path: {e['path']}, Value: {e['snippet']}" for e in evidence[:3]]
        )

        # System prompt enforces constraint: no made-up facts
        system_prompt = self._get_system_prompt(language)

        # User prompt with concrete evidence
        user_prompt = self._get_user_prompt(
            title, evidence_str, checks, recommended_actions, max_length, language
        )

        try:
            # Format input as messages list for OpenAI API
            response = self.llm.create_response(
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Low temp for consistency
                max_tokens=150,  # ~3-6 sentences
            )

            description = response.strip()

            # Ensure within max_length
            if len(description) > max_length:
                description = description[:max_length].rsplit(" ", 1)[0] + "..."

            return description
        except Exception as e:
            logger.error(f"LLM call failed for summarizer: {e}")
            raise

    def _get_system_prompt(self, language: str) -> str:
        """System prompt enforcing no hallucination"""
        if language == "korean":
            return """당신은 RCA(Root Cause Analysis) 가설 설명 전문가입니다.

주의사항:
1. 반드시 주어진 근거(Evidence)에만 기반해서만 설명을 작성하세요
2. 근거에 없는 사실을 절대로 만들거나 추측하지 마세요
3. 간결하고 명확하게 3-6문장으로 작성하세요
4. 한국어로 작성하세요"""
        else:
            return """You are an RCA hypothesis description expert.

Important constraints:
1. ONLY base descriptions on the provided evidence
2. NEVER make up facts or speculate beyond evidence
3. Keep descriptions concise: 3-6 sentences max
4. Write in English"""

    def _get_user_prompt(
        self,
        title: str,
        evidence_str: str,
        checks: List[str],
        actions: List[str],
        max_length: int,
        language: str,
    ) -> str:
        """User prompt with concrete evidence"""
        if language == "korean":
            return f"""다음 RCA 가설에 대한 간단한 설명을 작성하세요:

제목: {title}

근거(Evidence):
{evidence_str}

확인 체크리스트:
{chr(10).join(f"- {c}" for c in checks[:2])}

권장 조치:
{chr(10).join(f"- {a}" for a in actions[:2])}

위 근거에만 기반해서 {max_length}자 이내로 설명을 작성하세요. 근거 밖의 추론은 금지됩니다."""
        else:
            return f"""Write a brief description for this RCA hypothesis based ONLY on the evidence provided:

Title: {title}

Evidence:
{evidence_str}

Verification Checks:
{chr(10).join(f"- {c}" for c in checks[:2])}

Recommended Actions:
{chr(10).join(f"- {a}" for a in actions[:2])}

Write {max_length} chars max, based ONLY on evidence. NO speculation beyond evidence."""

    def _fallback_description(
        self, hypothesis: Dict[str, Any], language: str
    ) -> str:
        """Fallback: use evidence snippets when LLM fails"""
        evidence = hypothesis.get("evidence", [])

        if not evidence:
            return "No evidence snippets available." if language == "english" else "근거 정보 없음"

        snippets = [e.get("snippet", "")[:50] for e in evidence[:2]]
        snippet_str = " | ".join(s for s in snippets if s)

        if language == "korean":
            return f"근거: {snippet_str}"
        else:
            return f"Evidence: {snippet_str}"


def summarize_rca_results(
    hypotheses: List[Dict[str, Any]],
    use_llm: bool = True,
    language: str = "korean",
) -> List[Dict[str, Any]]:
    """
    Convenience function to summarize RCA results.

    Args:
        hypotheses: List of hypothesis dicts from RCAEngine.to_dict()
        use_llm: Whether to use LLM (set False to skip for cost/performance)
        language: Output language

    Returns:
        Hypotheses with descriptions populated
    """
    if not use_llm:
        # Add empty descriptions if LLM disabled
        for hyp in hypotheses:
            hyp["description"] = ""
        return hypotheses

    try:
        summarizer = RCASummarizer()
        return summarizer.summarize_hypotheses(hypotheses, language=language)
    except Exception as e:
        logger.error(f"RCA summarization failed: {e}")
        # Fallback: return without descriptions
        for hyp in hypotheses:
            hyp["description"] = ""
        return hypotheses
