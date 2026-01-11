"""
Script that sends a chat request (System + User) to Ollama and receives a JSON response.
"""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = os.getenv("OLLAMA_API_URL", "http://115.21.12.41:11434")
OLLAMA_ENDPOINT = f"{BASE_URL}/api/chat"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3coder-30b-cline:latest")


def call_ollama_chat(user_message: str, system_message: str) -> dict:
    """Sends a chat request to Ollama and returns the JSON parsed response."""
    
    messages = [
        {
            "role": "system",
            "content": system_message
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "format": "json"  # <--- [중요] 이 옵션이 있어야 확실한 JSON을 뱉습니다.
    }
    
    request = Request(
        OLLAMA_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        # 타임아웃 30초
        with urlopen(request, timeout=30) as response:
            response_data = json.load(response)
            
    except HTTPError as exc:
        raise RuntimeError(f"Ollama request failed with status {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Ollama at {OLLAMA_ENDPOINT}: {exc.reason}") from exc

    return extract_json_content(response_data)


def extract_json_content(payload: dict) -> dict:
    """Extracts the 'message.content' and tries to parse it as JSON. If not parseable, returns as error dict with raw content."""
    content_str = payload.get("message", {}).get("content", "")
    if not content_str:
        return {"content": ""}
    try:
        parsed = json.loads(content_str)
        if isinstance(parsed, (dict, list)):
            return parsed
        else:
            return {"content": parsed}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON", "raw_content": content_str}


def main() -> None:
    SYSTEM_PROMPT = (
        "You are a helpful assistant. "
        "Always respond in valid JSON format with keys: 'greeting', 'mood', 'suggestion'."
    )
    USER_PROMPT = "Hello! I am ready to code."
    try:
        result_dict = call_ollama_chat(USER_PROMPT, SYSTEM_PROMPT)
        print(json.dumps(result_dict, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
