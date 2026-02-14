"""Prompts for API Manager Copilot."""

import json
from typing import Any, Optional

SYSTEM_PROMPT = """You are an expert API designer and code generator. Your role is to help users create, modify, and improve REST APIs, SQL queries, and HTTP integrations.

You have deep knowledge of:
- RESTful API design principles (HTTP methods, status codes, resource modeling)
- SQL query optimization and security
- HTTP request/response patterns
- Parameter validation and error handling
- Authentication and security best practices
- JSON schema design and validation

When generating APIs:
1. Always prioritize security (parameterized queries, input validation, rate limiting)
2. Follow RESTful conventions (GET for retrieval, POST for creation, PUT for updates, DELETE for removal)
3. Include proper error handling and status codes
4. Provide REALISTIC request/response examples with actual data
5. Suggest improvements and best practices

IMPORTANT: Always include realistic examples:
- For POST/PUT APIs: include a request body with sample data
- For all APIs: include a response example showing the actual data structure
- Examples should be concrete and demonstrable, not generic

Your response MUST be valid JSON with the following structure:
{
  "api_draft": {
    "api_name": "name of the API",
    "description": "detailed description",
    "endpoint": "/api/path",
    "method": "GET|POST|PUT|DELETE",
    "logic_type": "sql|http|python|workflow",
    "logic_body": "the actual logic (SQL query, HTTP spec JSON, or code)",
    "param_schema": {"param_name": "description or schema object"},
    "tags": ["tag1", "tag2"]
  },
  "explanation": "why you designed it this way - include key design decisions",
  "confidence": 0.7,
  "suggestions": ["suggestion 1", "suggestion 2"],
  "http_spec": {
    "url": "https://...",
    "method": "GET|POST|PUT|DELETE",
    "headers": {"Header-Name": "value"},
    "body": null or {sample request body},
    "params": {"param_name": "sample_value"},
    "examples": [
      {"request": {request data}, "response": {response data}},
      {"request": {another request}, "response": {another response}}
    ]
  },
  "request_example": {actual sample request payload with realistic data},
  "response_example": {actual sample response payload with realistic data}
}

Focus on practicality, security, and clarity. Always explain your design decisions. Make examples concrete and useful."""


def build_user_prompt(
    prompt: str,
    logic_type: Optional[str] = None,
    api_draft: Optional[dict[str, Any]] = None,
    available_databases: Optional[list[str]] = None,
    common_headers: Optional[dict[str, str]] = None,
) -> str:
    """Build the user prompt for API copilot."""

    context_parts = []

    if logic_type:
        context_parts.append(f"API Logic Type: {logic_type}")

    if available_databases:
        context_parts.append(f"Available Databases: {', '.join(available_databases)}")

    if common_headers:
        context_parts.append(f"Common Headers:\n{json.dumps(common_headers, indent=2)}")

    if api_draft:
        context_parts.append(f"Current API Draft:\n{json.dumps(api_draft, indent=2)}")

    context_str = "\n\n".join(context_parts)

    if context_str:
        return f"""User Request:
{prompt}

Context:
{context_str}

Please generate or improve the API based on the above request and context."""
    else:
        return f"User Request:\n{prompt}\n\nPlease generate an API based on the above request."


def parse_llm_response(response_text: str) -> dict[str, Any]:
    """Parse LLM response and extract structured data.

    Handles JSON responses and extracts request/response examples.
    """

    # Try to extract JSON from the response
    try:
        # Look for JSON object in the response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')

        if start_idx >= 0 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx + 1]
            parsed = json.loads(json_str)

            # Validate expected fields
            if "api_draft" in parsed:
                # Extract request/response examples if not explicitly provided
                if not parsed.get("request_example") and parsed.get("http_spec"):
                    http_spec = parsed["http_spec"]
                    if http_spec.get("examples"):
                        examples = http_spec["examples"]
                        if len(examples) > 0:
                            parsed["request_example"] = examples[0].get("request", {})
                            parsed["response_example"] = examples[0].get("response", {})

                return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: return error
    return {
        "api_draft": {},
        "explanation": "Failed to parse API generation response",
        "confidence": 0.0,
        "suggestions": ["Please try again with a more specific request"],
        "request_example": None,
        "response_example": None
    }


def generate_example_request(api_draft: dict[str, Any]) -> dict[str, Any]:
    """Generate a reasonable example request based on API draft.

    Used as fallback when LLM doesn't provide explicit examples.
    """

    method = api_draft.get("method", "GET")
    param_schema = api_draft.get("param_schema", {})

    example = {}

    # Add parameters
    for param_name, param_info in param_schema.items():
        if isinstance(param_info, dict):
            param_type = param_info.get("type", "string")
            if param_type == "number":
                example[param_name] = 42
            elif param_type == "boolean":
                example[param_name] = True
            elif param_type == "array":
                example[param_name] = []
            else:
                example[param_name] = f"sample_{param_name}"
        else:
            example[param_name] = f"sample_{param_name}"

    return example


def generate_example_response(api_draft: dict[str, Any]) -> dict[str, Any]:
    """Generate a reasonable example response based on API draft.

    Used as fallback when LLM doesn't provide explicit examples.
    """

    return {
        "status": "success",
        "data": {
            "id": "example-id-123",
            "created_at": "2024-02-14T10:30:00Z",
            "message": "Operation completed successfully"
        }
    }
