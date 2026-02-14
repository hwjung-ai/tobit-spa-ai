"""
Convert Tool Registry to LLM Function Calling Format

This module provides utilities to convert Tool Assets from the registry
into OpenAI/Claude function calling format (tools parameter).
"""

from typing import Any, Dict, List

from core.logging import get_logger

from app.modules.ops.services.orchestration.tools.base import get_tool_registry

logger = get_logger(__name__)


def convert_tools_to_function_calling() -> List[Dict[str, Any]]:
    """
    Convert all available tools from ToolRegistry to function calling format.

    Returns:
        List of tools in OpenAI/Claude function calling format:
        [
            {
                "type": "function",
                "function": {
                    "name": "tool_name",
                    "description": "Tool description",
                    "parameters": {
                        "type": "object",
                        "properties": {...},
                        "required": [...]
                    }
                }
            },
            ...
        ]
    """
    tools = []
    registry = get_tool_registry()

    try:
        for name, tool in registry.get_available_tools().items():
            tool_function_spec = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description or f"Execute {name} tool",
                    "parameters": tool.input_schema
                    or {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }
            tools.append(tool_function_spec)
            logger.debug(f"Added tool to function calling: {name}")

        logger.info(f"Converted {len(tools)} tools to function calling format")
        return tools

    except Exception as exc:
        logger.error(f"Error converting tools to function calling: {str(exc)}")
        return []


def get_planning_tool_schema() -> Dict[str, Any]:
    """
    Get the tool schema for the planner itself (create_execution_plan).

    This tool is used by the LLM to create execution plans for OPS queries.

    Returns:
        Tool schema for create_execution_plan function
    """
    return {
        "type": "function",
        "function": {
            "name": "create_execution_plan",
            "description": "Create an execution plan for an IT operations query",
            "parameters": {
                "type": "object",
                "properties": {
                    "route": {
                        "type": "string",
                        "enum": ["direct", "plan", "reject"],
                        "description": "How to handle the query: direct (single tool), plan (multi-step), or reject (cannot answer)",
                    },
                    "intent": {
                        "type": "string",
                        "enum": [
                            "LOOKUP",
                            "AGGREGATE",
                            "PATH",
                            "EXPAND",
                            "LIST",
                            "HISTORY",
                            "STATUS",
                            "OTHER",
                        ],
                        "description": "User's intent (what they want to know)",
                    },
                    "ci_identifiers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "CI codes or identifiers mentioned in query (e.g., ['mes-server-06', 'app-service-01'])",
                    },
                    "output_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["text", "table", "chart", "network", "timeseries", "list"],
                        },
                        "description": "Expected output types (what format user wants)",
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recommended tool names from registry to use (e.g., ['ci_detail_lookup', 'maintenance_history_list'])",
                    },
                    "filters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {
                                    "type": "string",
                                    "description": "Filter field name (e.g., 'status', 'ci_type')",
                                },
                                "operator": {
                                    "type": "string",
                                    "enum": ["=", "!=", "ILIKE", "IN", ">", "<"],
                                    "description": "Comparison operator",
                                },
                                "value": {
                                    "description": "Filter value (can be string, number, or array)",
                                },
                            },
                            "required": ["field", "operator", "value"],
                        },
                        "description": "Optional filters to apply",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["config", "metric", "hist", "graph", "document", "all"],
                        "description": "OPS query mode to execute",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of why you chose this plan",
                    },
                },
                "required": ["route", "intent", "output_types"],
            },
        },
    }


def build_tools_for_llm_prompt(include_planner: bool = True) -> tuple[List[Dict[str, Any]], str]:
    """
    Build complete tools list and a descriptive text for LLM prompt.

    Args:
        include_planner: Whether to include the planner tool itself

    Returns:
        Tuple of (tools_list, tools_description_text)
    """
    all_tools = []
    tool_names = []

    # Add available tools from registry
    available_tools = convert_tools_to_function_calling()
    all_tools.extend(available_tools)
    for tool in available_tools:
        tool_names.append(tool["function"]["name"])

    # Add planner tool if requested
    if include_planner:
        planner_tool = get_planning_tool_schema()
        all_tools.append(planner_tool)
        tool_names.append("create_execution_plan")

    # Build description text
    tools_desc = f"""
Available tools ({len(all_tools)} total):
{chr(10).join([f"  - {name}" for name in tool_names])}

Use these tools to answer the user's query. Call the create_execution_plan tool
to determine which tools to use and how to use them.
"""

    return all_tools, tools_desc


def extract_tool_call_from_response(response: Any) -> Dict[str, Any] | None:
    """
    Extract tool call from LLM response.

    Args:
        response: Response object from LLM API

    Returns:
        Tool call dict with 'name' and 'input' keys, or None if no tool call
    """
    try:
        # Try to get output_items from response
        if hasattr(response, "output_items"):
            items = response.output_items
        elif isinstance(response, dict):
            items = response.get("output_items", [])
        else:
            return None

        # Find first tool_use item
        for item in items:
            if isinstance(item, dict):
                if item.get("type") == "tool_use":
                    return {
                        "name": item.get("name"),
                        "input": item.get("input", {}),
                    }
            elif hasattr(item, "type") and item.type == "tool_use":
                return {
                    "name": getattr(item, "name", None),
                    "input": getattr(item, "input", {}),
                }

        return None

    except Exception as exc:
        logger.warning(f"Error extracting tool call: {str(exc)}")
        return None
