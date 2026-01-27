"""
Domain Classifier - LLM-based automatic domain detection.

This module uses LLM to automatically classify which domain a user question
belongs to, enabling dynamic routing to the appropriate domain planner.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.llm.client import get_llm_client
from core.logging import get_logger

from app.modules.ops.services.domain.registry import DomainRegistry

logger = get_logger(__name__)


class DomainClassifier:
    """
    LLM-based domain classifier for automatic domain detection.

    Analyzes user questions and determines which domain (CI, Audit, Finance, etc.)
    should handle the question.
    """

    def __init__(self, registry: DomainRegistry | None = None):
        """
        Initialize the domain classifier.

        Args:
            registry: Optional domain registry. If None, uses global registry.
        """
        self.registry = registry
        self._domain_descriptions: dict[str, str] | None = None

    def _get_domain_descriptions(self) -> dict[str, str]:
        """
        Get descriptions for all registered domains.

        Returns:
            Dictionary mapping domain names to descriptions
        """
        if self._domain_descriptions is not None:
            return self._domain_descriptions

        self._domain_descriptions = {}

        if self.registry:
            metadata_dict = self.registry.list_metadata()
            for domain, metadata in metadata_dict.items():
                desc = f"{metadata.description}\n"
                desc += f"키워드: {', '.join(metadata.keywords[:10])}"
                self._domain_descriptions[domain] = desc
        else:
            # Fallback to default descriptions
            self._domain_descriptions = {
                "ci": "IT 인프라, 서버, 애플리케이션 구성 정보\n"
                       "키워드: 서버, cpu, memory, 구성, 메트릭",
            }

        return self._domain_descriptions

    async def classify_domain(
        self,
        question: str,
        use_llm: bool = True,
    ) -> tuple[str, float, str]:
        """
        Classify which domain a question belongs to.

        Args:
            question: User question to classify
            use_llm: Whether to use LLM for classification (default: True)

        Returns:
            Tuple of (domain_name, confidence, reasoning)
        """
        normalized = question.strip()

        # Try keyword-based classification first (faster)
        if self.registry:
            planner = await self.registry.find_planner_by_keywords(normalized)
            if planner:
                logger.info(
                    f"Domain classified by keyword: {planner.domain}",
                    extra={"question": normalized[:100]}
                )
                return (
                    planner.domain,
                    0.8,
                    f"Keyword match: {planner.domain} domain keywords found in question"
                )

        # Fallback to LLM-based classification
        if use_llm:
            try:
                return await self._classify_with_llm(normalized)
            except Exception as e:
                logger.warning(f"LLM classification failed: {e}")
                # Fallback to default domain

        # Default fallback
        default_domain = self._get_default_domain()
        logger.info(
            f"Using default domain: {default_domain}",
            extra={"question": normalized[:100]}
        )
        return (
            default_domain,
            0.5,
            "No specific domain detected, using default domain"
        )

    async def _classify_with_llm(
        self, question: str
    ) -> tuple[str, float, str]:
        """
        Use LLM to classify the question domain.

        Args:
            question: User question to classify

        Returns:
            Tuple of (domain_name, confidence, reasoning)
        """
        domain_descriptions = self._get_domain_descriptions()

        # Build domain list for the prompt
        domain_list = "\n".join([
            f"- {domain}: {desc}"
            for domain, desc in domain_descriptions.items()
        ])

        prompt = f"""다음 질문이 어떤 도메인에 속하는지 분류하세요.

도메인 목록:
{domain_list}

질문: {question}

답변 형식 (JSON only, no markdown):
{{
  "domain": "도메인 이름 (예: ci, audit, finance 중 하나)",
  "confidence": 0.0 ~ 1.0 사이의 신뢰도 숫자,
  "reasoning": "분류 이유 (한국어, 2-3문장)"
}}
"""

        try:
            llm = get_llm_client()
            response = llm.create_response(
                model="gpt-4o-mini",
                input=[{"role": "user", "content": prompt}],
                temperature=0,
            )

            content = llm.get_output_text(response)
            result = self._extract_json(content)

            domain = result.get("domain", "").lower()
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "No reasoning provided")

            # Validate domain exists
            if self.registry and not self.registry.is_registered(domain):
                # Try to find partial match
                for registered_domain in self.registry.list_domains():
                    if registered_domain in domain or domain in registered_domain:
                        domain = registered_domain
                        break
                else:
                    # Use default domain
                    domain = self._get_default_domain()
                    confidence = max(confidence * 0.5, 0.3)
                    reasoning = f"Unknown domain '{result.get('domain')}', using default: {reasoning}"

            logger.info(
                f"Domain classified by LLM: {domain} (confidence: {confidence:.2f})",
                extra={
                    "question": question[:100],
                    "reasoning": reasoning[:200]
                }
            )

            return domain, confidence, reasoning

        except Exception as e:
            logger.error(f"LLM domain classification error: {e}")
            raise

    def _extract_json(self, text: str) -> dict[str, Any]:
        """
        Extract JSON from LLM response.

        Handles markdown code blocks and malformed JSON.

        Args:
            text: LLM response text

        Returns:
            Parsed JSON dict
        """
        # Remove markdown code blocks
        text = re.sub(r'```(?:json)?\s*', '', text.strip())

        # Find JSON object
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            text = match.group(0)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return {
                "domain": "ci",
                "confidence": 0.5,
                "reasoning": f"JSON parsing failed, using default: {str(e)}"
            }

    def _get_default_domain(self) -> str:
        """
        Get the default domain name.

        Returns:
            Default domain name (typically "ci")
        """
        if self.registry:
            default = self.registry.get_default_domain()
            if default:
                return default
        return "ci"


# Global classifier instance
_global_domain_classifier: DomainClassifier | None = None


def get_domain_classifier(registry: DomainRegistry | None = None) -> DomainClassifier:
    """
    Get the global domain classifier, creating it if necessary.

    Args:
        registry: Optional domain registry to use

    Returns:
        DomainClassifier instance
    """
    global _global_domain_classifier
    if _global_domain_classifier is None:
        _global_domain_classifier = DomainClassifier(registry)
    return _global_domain_classifier


async def classify_question_domain(
    question: str,
    use_llm: bool = True,
) -> tuple[str, float, str]:
    """
    Convenience function to classify a question's domain.

    Args:
        question: User question to classify
        use_llm: Whether to use LLM for classification

    Returns:
        Tuple of (domain_name, confidence, reasoning)
    """
    classifier = get_domain_classifier()
    return await classifier.classify_domain(question, use_llm)
