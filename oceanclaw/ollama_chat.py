"""Ollama chat client."""

from __future__ import annotations

from .ollama_embed import post_json


def chat(
    messages: list[dict[str, str]],
    model: str,
    base_url: str,
    timeout: int,
    temperature: float = 0.1,
) -> str:
    endpoint = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    response = post_json(endpoint, payload, timeout)
    message = response.get("message", {})
    content = message.get("content", "")
    if not content:
        raise RuntimeError(f"Ollama did not return chat content. Check model: {model}")
    return content.strip()
