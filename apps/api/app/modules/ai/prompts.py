"""Screen Copilot Prompt Templates."""

import json
from typing import Any

SYSTEM_PROMPT = """You are a Screen Editor AI Copilot. Your task is to generate JSON Patch operations (RFC6902) to modify screen schemas based on user requests.

## Available Component Types
- text: Display text content
- markdown: Markdown formatted content
- button: Clickable button with actions
- input: Text input field
- form: Form container with inputs
- table: Data table with columns and rows
- chart: Chart visualization (line, bar, pie, etc.)
- badge: Status badge or label
- tabs: Tab container with multiple panels
- accordion: Collapsible content sections
- modal: Popup modal dialog
- keyvalue: Key-value pair display
- divider: Horizontal or vertical divider
- row: Horizontal layout container
- column: Vertical layout container

## Common Component Props
- text: content, size, color, weight
- button: label, variant (primary/secondary/outline), disabled, loading
- input: placeholder, type (text/number/password), value, disabled
- table: columns, rows, selectable, pagination
- chart: type, data, options
- modal: title, open, size

## JSON Patch Operations (RFC6902)
- {"op": "add", "path": "/components/-", "value": {...}} - Add new component
- {"op": "remove", "path": "/components/0"} - Remove component
- {"op": "replace", "path": "/components/0/props/label", "value": "New"} - Update value
- {"op": "move", "from": "/components/0", "path": "/components/2"} - Reorder

## Binding Syntax
- {{state.field}} - Bind to state
- {{context.user_id}} - Bind to context
- {{inputs.search}} - Bind to inputs

## Response Format
Return ONLY a valid JSON object (no markdown, no explanation outside JSON):
{
  "patch": [...],
  "explanation": "Brief explanation",
  "confidence": 0.9,
  "suggestions": ["Optional suggestions"]
}

IMPORTANT: 
- Return ONLY the JSON object, no other text
- patch must be an array (can be empty)
- confidence must be between 0 and 1
- If you cannot fulfill the request, return empty patch with low confidence"""


def build_user_prompt(
    screen_schema: dict[str, Any],
    prompt: str,
    selected_component: str | None = None,
    available_handlers: list[str] | None = None,
    state_paths: list[str] | None = None,
) -> str:
    """Build the user prompt for the LLM."""

    parts = []

    # Screen schema
    parts.append("## Current Screen Schema")
    parts.append("```json")
    parts.append(json.dumps(screen_schema, indent=2, ensure_ascii=False))
    parts.append("```")
    parts.append("")

    # Selected component
    if selected_component:
        parts.append(f"## Selected Component: `{selected_component}`")
        # Find and show the selected component
        components = screen_schema.get("components", [])
        for i, comp in enumerate(components):
            if comp.get("id") == selected_component:
                parts.append("```json")
                parts.append(json.dumps(comp, indent=2, ensure_ascii=False))
                parts.append("```")
                parts.append(f"Component index: {i}")
                break
        parts.append("")

    # Available handlers
    if available_handlers:
        parts.append("## Available Action Handlers")
        for handler in available_handlers[:20]:  # Limit to 20
            parts.append(f"- {handler}")
        parts.append("")

    # State paths
    if state_paths:
        parts.append("## Available State Paths")
        for path in state_paths[:30]:  # Limit to 30
            parts.append(f"- {path}")
        parts.append("")

    # User request
    parts.append("## User Request")
    parts.append(prompt)

    return "\n".join(parts)


def parse_llm_response(response_text: str) -> dict[str, Any]:
    """Parse LLM response text to extract JSON."""

    # Strip whitespace
    text = response_text.strip()

    # Try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            json_str = text[start:end].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # Try finding JSON object in text
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # Return default empty response
    return {
        "patch": [],
        "explanation": "Failed to parse LLM response",
        "confidence": 0.0,
        "suggestions": []
    }
