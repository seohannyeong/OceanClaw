"""Provider selector for embedding and answer generation."""

from __future__ import annotations

from typing import List

from . import config, gemini, ollama


def _provider():
    if config.LLM_PROVIDER == "ollama":
        return ollama
    if config.LLM_PROVIDER == "gemini":
        return gemini
    raise RuntimeError(
        f"지원하지 않는 LLM_PROVIDER입니다: {config.LLM_PROVIDER}. "
        "`ollama` 또는 `gemini`를 사용하세요."
    )


def embed_texts(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    return _provider().embed_texts(texts, task_type=task_type)


def embed_query(text: str) -> List[float]:
    return _provider().embed_query(text)


def generate_answer(query: str, context: str) -> str:
    return _provider().generate_answer(query, context)
