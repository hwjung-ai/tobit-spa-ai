"""
Query Asset Selector - Select appropriate Query Assets based on user questions.

This module provides functionality to match user questions with available
Query Assets by analyzing keywords and metadata.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class QueryAssetSelector:
    """
    Selects the most appropriate Query Asset for a given question.

    Uses keyword matching and metadata comparison to find the best
    Query Asset to execute.
    """

    def __init__(self, query_assets: Dict[str, Any]):
        """
        Initialize the selector with available Query Assets.

        Args:
            query_assets: Dictionary mapping asset names to asset data
                         Each asset should have: name, keywords, sql, output_type
        """
        self.query_assets = query_assets
        self.logger = logger

    def select_asset(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Select the best Query Asset for the given question.

        Args:
            question: User question/query

        Returns:
            The selected Query Asset dict, or None if no good match found
        """
        if not self.query_assets:
            return None

        # Extract keywords from question
        question_keywords = self._extract_keywords(question)

        if not question_keywords:
            return None

        # Score each asset
        best_asset = None
        best_score = 0.0

        for asset_name, asset in self.query_assets.items():
            score = self._score_asset(question, question_keywords, asset)

            if score > best_score:
                best_score = score
                best_asset = asset

            self.logger.debug(
                f"Asset {asset_name} score: {score:.2f}",
                extra={"keywords": asset.get("keywords", [])}
            )

        # Return asset only if match score is significant
        if best_score > 0.3:
            self.logger.info(
                f"Selected Query Asset: {best_asset.get('name', 'unknown')} (score: {best_score:.2f})"
            )
            return best_asset

        self.logger.warning(f"No good Query Asset match for question (best score: {best_score:.2f})")
        return None

    def _extract_keywords(self, question: str) -> list[str]:
        """
        Extract important keywords from the question.

        Args:
            question: User question

        Returns:
            List of important keywords
        """
        # Simple keyword extraction: split and filter
        stop_words = {
            'what', 'how', 'many', 'is', 'are', 'the', 'a', 'an',
            'in', 'of', 'to', 'and', 'or', 'with', 'by', 'for',
            'can', 'will', 'do', 'did', 'would', 'could', 'should',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'tell', 'show', 'me', 'us', 'you', 'we', 'i', 'they',
            'currently', 'today', 'we', 'the', 'this', 'that',
            'have', 'there', 'been', 'been', 'number', 'count'
        }

        words = question.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords

    def _score_asset(
        self,
        question: str,
        question_keywords: list[str],
        asset: Dict[str, Any]
    ) -> float:
        """
        Score an asset based on keyword matching.

        Args:
            question: User question
            question_keywords: Extracted keywords from question
            asset: Asset to score

        Returns:
            Score between 0 and 1
        """
        score = 0.0

        # Get asset keywords/metadata
        asset_keywords = asset.get("keywords", [])
        asset_name = asset.get("name", "").lower()

        # Match keywords
        if asset_keywords:
            matched_keywords = sum(
                1 for kw in question_keywords
                if any(akw.lower() in kw for akw in asset_keywords)
                   or any(kw in akw.lower() for akw in asset_keywords)
            )
            keyword_score = matched_keywords / max(len(question_keywords), 1)
            score += keyword_score * 0.7  # Weight: 70%

        # Match asset name in question
        if asset_name and asset_name in question.lower():
            score += 0.3  # Weight: 30%

        return min(score, 1.0)


def select_query_asset(question: str, assets: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convenience function to select a Query Asset.

    Args:
        question: User question
        assets: Available Query Assets

    Returns:
        Selected Query Asset or None
    """
    selector = QueryAssetSelector(assets)
    return selector.select_asset(question)
