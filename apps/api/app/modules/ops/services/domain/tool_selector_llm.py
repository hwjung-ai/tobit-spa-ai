"""
LLM-based Tool Selector for Generic Orchestration System.

This module implements an LLM-based tool selection mechanism that analyzes
user questions and selects appropriate tools from the registry based on
tool descriptions and input schemas.
"""

from __future__ import annotations

import json
from typing import Any

from core.logging import get_logger
from pydantic import BaseModel, Field

from app.modules.ops.services.orchestration.tools.base import get_tool_registry

logger = get_logger(__name__)


class ToolSelection(BaseModel):
    """Selected tool with confidence and reasoning."""

    tool_name: str = Field(..., description="Name of the selected tool")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)"
    )
    reasoning: str = Field(..., description="Reason for selecting this tool")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Extracted parameters for the tool"
    )


class ToolSelectionResult(BaseModel):
    """Result of tool selection."""

    tools: list[ToolSelection] = Field(default_factory=list)
    execution_order: str = Field(
        default="sequential", description="sequential or parallel"
    )


class LLMToolSelector:
    """
    LLM-based tool selector.

    Analyzes user questions and selects appropriate tools from the registry
    based on tool descriptions and input schemas.
    """

    def __init__(self):
        """Initialize the tool selector."""
        self._prompt_template: str | None = None

    def _get_fallback_prompt(self) -> str:
        """Get fallback prompt template."""
        return """당신은 사용자 질문에 적합한 도구(Tool)를 선택하는 AI입니다.

사용 가능한 도구 목록:
{tool_descriptions}

사용자 질문:
{question}

응답 형식 (반드시 JSON으로만 응답):
{{
  "tools": [
    {{
      "tool_name": "도구 이름",
      "confidence": 0.0~1.0 사이의 신뢰도,
      "reasoning": "선택 이유",
      "parameters": {{"파라미터명": "값"}}
    }}
  ],
  "execution_order": "sequential" 또는 "parallel"
}}

주의사항:
1. 질문에 가장 적합한 도구를 선택하세요
2. 여러 도구가 필요하면 모두 선택하세요
3. 도구 순서가 중요하면 sequential, 독립적이면 parallel로 지정하세요
4. 파라미터는 질문에서 추출할 수 있는 값만 포함하세요
5. 반드시 유효한 JSON만 출력하세요

JSON 응답:"""

    async def _load_prompt(self) -> str:
        """Load tool selector prompt from asset or use fallback."""
        if self._prompt_template:
            return self._prompt_template

        try:
            from app.modules.asset_registry.loader import load_prompt_asset

            prompt_data = load_prompt_asset(
                scope="generic", name="tool_selector", engine="openai"
            )
            if prompt_data and prompt_data.get("template"):
                self._prompt_template = prompt_data["template"]
                return self._prompt_template
        except Exception as e:
            logger.debug(f"Failed to load tool_selector prompt: {e}")

        self._prompt_template = self._get_fallback_prompt()
        return self._prompt_template

    def _get_schema_info_for_tool(self, tool_name: str) -> str | None:
        """Get schema information for a tool if available via catalog_ref."""
        try:
            from app.modules.asset_registry.loader import (
                load_catalog_asset,
                load_tool_asset,
            )

            tool_asset = load_tool_asset(tool_name)
            if not tool_asset:
                return None

            # First try tool_catalog_ref (newly connected catalogs)
            catalog_ref = tool_asset.get("tool_catalog_ref")

            # Fallback to old schema_ref in tool_config for backward compatibility
            if not catalog_ref:
                tool_config = tool_asset.get("tool_config", {})
                catalog_ref = tool_config.get("schema_ref")

            if not catalog_ref:
                return None

            # Load catalog asset by name
            catalog_asset = load_catalog_asset(catalog_ref)
            if not catalog_asset:
                return None

            catalog = catalog_asset.get("catalog", {})
            tables = catalog.get("tables", [])

            # Build schema summary (only enabled tables)
            enabled_tables = [t for t in tables if t.get("enabled", True)]

            if not enabled_tables:
                return None

            schema_lines = []
            for table in enabled_tables[:5]:  # Limit to first 5 tables
                table_name = table.get("name", "")
                columns = table.get("columns", [])
                # Show only first 5 columns per table
                col_names = [
                    f"{c.get('column_name')} ({c.get('data_type')})"
                    for c in columns[:5]
                ]
                col_str = ", ".join(col_names)
                if len(columns) > 5:
                    col_str += f", ... ({len(columns) - 5} more)"
                schema_lines.append(f"    * {table_name}: {col_str}")

            if len(enabled_tables) > 5:
                schema_lines.append(f"    ... and {len(enabled_tables) - 5} more tables")

            return "\n".join(schema_lines)

        except Exception as e:
            logger.debug(f"Failed to load schema info for tool {tool_name}: {e}")
            return None

    def _build_tool_descriptions(self) -> str:
        """Build tool descriptions from registry, including schema info."""
        registry = get_tool_registry()
        tools = registry.get_available_tools()

        lines = []
        for tool_name, tool in tools.items():
            description = getattr(tool, "description", "") or "(설명 없음)"
            input_schema = getattr(tool, "input_schema", {})

            # Summarize input parameters
            props = input_schema.get("properties", {}) if input_schema else {}
            params_str = ", ".join(props.keys()) if props else "(파라미터 없음)"

            lines.append(f"- {tool_name}: {description}")
            lines.append(f"  입력: {params_str}")

            # Try to add schema information if available
            schema_info = self._get_schema_info_for_tool(tool_name)
            if schema_info:
                lines.append("  데이터베이스 스키마:")
                lines.append(schema_info)

        return "\n".join(lines)

    async def select_tools(
        self, question: str, context: dict[str, Any] | None = None
    ) -> ToolSelectionResult:
        """
        Select appropriate tools for the given question.

        Args:
            question: User question
            context: Optional context (tenant_id, session info, etc.)

        Returns:
            ToolSelectionResult with selected tools
        """
        logger.info(f"Selecting tools for: {question[:50]}...")

        # Build prompt
        template = await self._load_prompt()
        tool_descriptions = self._build_tool_descriptions()

        if not tool_descriptions.strip():
            logger.warning("No tools registered in registry")
            return ToolSelectionResult(tools=[], execution_order="sequential")

        prompt = template.format(
            tool_descriptions=tool_descriptions,
            question=question,
        )

        # Call LLM
        try:
            from app.modules.ops.services.orchestration.planner.planner_llm import (
                call_openai_json,
            )

            response = await call_openai_json(
                prompt=prompt,
                system_message="You are a tool selection assistant. Always respond with valid JSON only.",
                temperature=0.1,
            )

            result = self._parse_response(response)
            logger.info(
                f"Selected {len(result.tools)} tools: {[t.tool_name for t in result.tools]}"
            )
            return result

        except Exception as e:
            logger.error(f"LLM tool selection failed: {e}")
            # Fallback: try keyword matching
            return await self._fallback_keyword_matching(question)

    def _parse_response(self, response: str | dict) -> ToolSelectionResult:
        """Parse LLM response into ToolSelectionResult."""
        if isinstance(response, str):
            # Clean up response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())
        else:
            data = response

        tools = []
        for tool_data in data.get("tools", []):
            selection = ToolSelection(
                tool_name=tool_data.get("tool_name", ""),
                confidence=float(tool_data.get("confidence", 0.5)),
                reasoning=tool_data.get("reasoning", ""),
                parameters=tool_data.get("parameters", {}),
            )
            if selection.tool_name:
                tools.append(selection)

        return ToolSelectionResult(
            tools=tools,
            execution_order=data.get("execution_order", "sequential"),
        )

    async def _fallback_keyword_matching(
        self, question: str
    ) -> ToolSelectionResult:
        """Fallback tool selection using keyword matching."""
        registry = get_tool_registry()
        tools = registry.get_available_tools()
        question_lower = question.lower()

        matched_tools = []
        for tool_name, tool in tools.items():
            description = getattr(tool, "description", "") or ""
            description_lower = description.lower()

            # Simple keyword matching
            keywords = tool_name.split("_") + description_lower.split()
            for keyword in keywords:
                if len(keyword) > 2 and keyword in question_lower:
                    matched_tools.append(
                        ToolSelection(
                            tool_name=tool_name,
                            confidence=0.6,
                            reasoning=f"Keyword match: {keyword}",
                            parameters={},
                        )
                    )
                    break

        return ToolSelectionResult(
            tools=matched_tools,
            execution_order="sequential",
        )


# Global selector instance
_global_tool_selector: LLMToolSelector | None = None


def get_tool_selector() -> LLMToolSelector:
    """Get the global tool selector instance."""
    global _global_tool_selector
    if _global_tool_selector is None:
        _global_tool_selector = LLMToolSelector()
    return _global_tool_selector


async def select_tools_for_question(
    question: str, context: dict[str, Any] | None = None
) -> ToolSelectionResult:
    """
    Select tools for a question using the global selector.

    Convenience function for tool selection.
    """
    selector = get_tool_selector()
    return await selector.select_tools(question, context)
