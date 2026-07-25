"""Ollama embedding client."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import List


def post_json(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise RuntimeError(
            "Could not connect to Ollama. Make sure Ollama is running."
        ) from exc


def check_ollama(base_url: str, timeout: int) -> None:
    request = urllib.request.Request(f"{base_url.rstrip('/')}/api/tags", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout):
            return
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise RuntimeError(
            "Could not connect to Ollama. Start Ollama and pull an embedding model."
        ) from exc


def embed_text(text: str, model: str, base_url: str, timeout: int) -> List[float]:
    endpoint = f"{base_url.rstrip('/')}/api/embed"
    payload = {"model": model, "input": text}

    try:
        response = post_json(endpoint, payload, timeout)
        embeddings = response.get("embeddings")
        if embeddings and isinstance(embeddings, list):
            return embeddings[0]
    except RuntimeError:
        raise
    except Exception:
        pass

    endpoint = f"{base_url.rstrip('/')}/api/embeddings"
    payload = {"model": model, "prompt": text}
    response = post_json(endpoint, payload, timeout)
    embedding = response.get("embedding")
    if not embedding:
        raise RuntimeError(
            f"Ollama did not return an embedding. Check model: {model}"
        )
    return embedding


def embed_texts(
    texts: list[str],
    model: str,
    base_url: str,
    timeout: int,
) -> list[list[float]]:
    return [embed_text(text, model, base_url, timeout) for text in texts]
