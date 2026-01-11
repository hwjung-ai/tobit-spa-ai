"""Minimal script that uses the project's OpenAI client to send a 'hello?' prompt."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Make sure the apps/api package is importable when this script runs from the repo root.
sys.path.append(str(ROOT / "apps" / "api"))

from app.llm.client import get_llm_client  # type: ignore[import]  # path is injected above


def send_hello() -> str:
    """Send a simple `hello?` prompt through the shared LLM client."""
    prompt = "hello?"
    client = get_llm_client()
    response: Any = client.create_response(prompt)
    return client.get_output_text(response).strip() or "<no text received>"


def main() -> None:
    """Execute the sample call and print the assistant text."""
    output = send_hello()
    print(output)


if __name__ == "__main__":
    main()
