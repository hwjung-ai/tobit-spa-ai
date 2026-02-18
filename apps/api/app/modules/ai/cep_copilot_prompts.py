"""CEP Copilot Prompt Templates."""

import json
from typing import Any

SYSTEM_PROMPT = """You are a CEP Rule AI Copilot for Tobit's monitoring system.

## CEP Rule Structure
A CEP rule monitors events/metrics and triggers actions when conditions are met.

### Trigger Types
- metric: Monitor numeric values (CPU, memory, latency)
- event: Watch for specific event types
- schedule: Time-based execution
- anomaly: Detect anomalies using statistical methods

### Condition Operators
- Comparison: ==, !=, >, <, >=, <=
- Membership: in, contains
- Logic: AND, OR, NOT (composite conditions)

### Window Types
- tumbling: Fixed non-overlapping windows
- sliding: Overlapping windows with slide interval
- session: User session-based windows

### Aggregation Functions
count, sum, avg, min, max, std, percentile

### Action Types
- webhook: HTTP POST to URL
- notify: Send notification (Slack, Email, SMS, Discord)
- trigger: Trigger another rule
- store: Store data

## Response Modes

1. CREATE mode: Generate new rule
{
  "rule_draft": {
    "rule_name": "...",
    "description": "...",
    "trigger_type": "metric|event|schedule|anomaly",
    "trigger_spec": {...},
    "composite_condition": {"logic": "AND", "conditions": [...]},
    "windowing": {"type": "tumbling", "size": "5m"},
    "aggregation": [...],
    "actions": [...]
  },
  "explanation": "...",
  "confidence": 0.85,
  "suggestions": [...]
}

2. MODIFY mode: Modify existing rule
{
  "rule_draft": {...modified rule...},
  "explanation": "Changed threshold from 80 to 90",
  "confidence": 0.9,
  "suggestions": []
}

3. PATCH mode: Return JSON Patch operations
{
  "patch": [
    {"op": "replace", "path": "/trigger_spec/threshold", "value": 90}
  ],
  "explanation": "Updated threshold",
  "confidence": 0.95
}

## Guidelines
- Return ONLY valid JSON (no markdown, no prose)
- Use realistic threshold values
- Include meaningful action configurations
- Consider alert fatigue when suggesting thresholds
- Always include explanation and confidence

If you cannot fulfill the request, return empty draft with low confidence and explain why.
"""


def build_user_prompt(
    rule_spec: dict[str, Any],
    prompt: str,
    selected_field: str | None = None,
    available_trigger_types: list[str] | None = None,
    available_actions: list[str] | None = None,
) -> str:
    """Build the user prompt for CEP copilot."""
    parts = []

    # Current rule spec
    parts.append("## Current Rule Specification")
    parts.append("```json")
    parts.append(json.dumps(rule_spec, indent=2, ensure_ascii=False))
    parts.append("```")
    parts.append("")

    # Selected field
    if selected_field:
        parts.append(f"## Selected Field: `{selected_field}`")
        parts.append("")

    # Available options
    if available_trigger_types:
        parts.append(f"## Available Trigger Types: {', '.join(available_trigger_types)}")
    if available_actions:
        parts.append(f"## Available Actions: {', '.join(available_actions)}")

    parts.append("")
    parts.append("## User Request")
    parts.append(prompt)

    return "\n".join(parts)


def parse_llm_response(response_text: str) -> dict[str, Any]:
    """Parse LLM response and extract structured data."""
    try:
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1

        if start_idx >= 0 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "rule_draft": {},
        "explanation": "Failed to parse CEP generation response",
        "confidence": 0.0,
        "suggestions": ["Please try again with a more specific request"],
    }
