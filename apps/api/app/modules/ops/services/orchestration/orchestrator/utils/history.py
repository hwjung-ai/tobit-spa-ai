"""History utilities for orchestration.

This module handles history-related fallback and filtering logic.
"""

from typing import Any, Dict, List

from app.modules.ops.services.orchestration.blocks import text_block

# History fallback keywords
HISTORY_FALLBACK_KEYWORDS = {
    "이력",
    "작업",
    "점검",
    "history",
    "log",
    "이벤트",
    "기록",
}


def history_fallback_for_question(
    question: str,
) -> tuple[List[Dict[str, Any]], str] | None:
    """Check if question should trigger history fallback.

    This checks if the user question contains history-related keywords.
    If so, suggests using history mode or tool assets instead.

    Args:
        question: User question text

    Returns:
        Tuple of (fallback_blocks, reason) if should trigger, None otherwise
    """
    text = (question or "").lower()
    if not any(keyword in text for keyword in HISTORY_FALLBACK_KEYWORDS):
        return None

    # Return fallback message
    return [
        text_block(
            "이력 조회 기능이 준비중입니다. 이력 탭을 이용해주세요.",
            title="History fallback",
        )
    ], "History tool not available"
