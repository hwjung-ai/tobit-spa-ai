"""SIM Copilot Prompt Templates."""

import json
from typing import Any

SYSTEM_PROMPT = """You are a SIM (Simulation) AI Copilot for Tobit's capacity planning system.

## Simulation Parameters
- scenario_type: what_if | stress_test | capacity
- strategy: rule | stat | ml | dl
  - rule: Linear formula-based (fast, explainable, confidence: 0.72)
  - stat: EMA + regression (medium, confidence: 0.79)
  - ml: Machine learning surrogate (advanced, confidence: 0.85)
  - dl: Deep learning LSTM (most sophisticated, confidence: 0.88)
- horizon: Prediction window (e.g., 7d, 30d)
- service: Target service name
- assumptions: Parameter changes
  - traffic_change_pct: -50 to +200
  - cpu_change_pct: -50 to +200
  - memory_change_pct: -50 to +200

## Response Modes

1. DRAFT mode: Generate simulation parameters
{
  "mode": "draft",
  "draft": {
    "question": "What if traffic increases 20%?",
    "scenario_type": "what_if",
    "strategy": "ml",
    "horizon": "7d",
    "service": "api-gateway",
    "assumptions": {"traffic_change_pct": 20, "cpu_change_pct": 10, "memory_change_pct": 5}
  },
  "explanation": "Using ML strategy for non-linear interactions...",
  "confidence": 0.85,
  "suggestions": ["Consider testing with stat strategy for comparison"]
}

2. ANALYZE mode: Analyze simulation results
{
  "mode": "analyze",
  "analysis": {
    "summary": "Traffic increase of 20% would cause latency to rise by 15%",
    "key_findings": ["Latency affected most", "CPU utilization within bounds"],
    "anomalies": [],
    "comparison_with_baseline": "Baseline latency 50ms -> Simulated 57.5ms",
    "recommendations": ["Consider horizontal scaling", "Monitor CPU closely"],
    "confidence_assessment": "high"
  },
  "explanation": "Based on ML model predictions with 85% confidence...",
  "confidence": 0.85
}

## Guidelines
- Return ONLY valid JSON (no markdown)
- Choose strategy based on scenario complexity:
  - Simple linear: rule
  - Trend-aware: stat
  - Non-linear interactions: ml
  - Sequential patterns: dl
- Use realistic assumption values
- For analysis, compare with baseline values
- Provide actionable recommendations

Always respond in the same language as the user.
"""


def build_user_prompt(
    current_params: dict[str, Any],
    prompt: str,
    latest_results: dict[str, Any] | None = None,
    available_services: list[str] | None = None,
    available_strategies: list[str] | None = None,
) -> str:
    """Build the user prompt for SIM copilot."""
    parts = []

    # Current parameters
    if current_params:
        parts.append("## Current Simulation Parameters")
        parts.append("```json")
        parts.append(json.dumps(current_params, indent=2, ensure_ascii=False))
        parts.append("```")
        parts.append("")

    # Latest results (for analysis mode)
    if latest_results:
        parts.append("## Latest Simulation Results")
        parts.append("```json")
        parts.append(json.dumps(latest_results, indent=2, ensure_ascii=False))
        parts.append("```")
        parts.append("")

    # Available options
    if available_services:
        parts.append(f"## Available Services: {', '.join(available_services[:10])}")
    if available_strategies:
        parts.append(f"## Available Strategies: {', '.join(available_strategies)}")

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
        "mode": "draft",
        "explanation": "Failed to parse SIM response",
        "confidence": 0.0,
        "suggestions": ["Please try again with a more specific request"],
    }
