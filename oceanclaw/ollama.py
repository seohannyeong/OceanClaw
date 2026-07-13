"""Ollama local LLM helper: embeddings + answer generation."""

from __future__ import annotations

import json
from typing import Any, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import config


SYSTEM_PROMPT = (
    "당신은 선박 기관실 정비를 돕는 전문 AI 어시스턴트입니다.\n"
    "규칙:\n"
    "1. 반드시 한국어로, 기관사가 현장에서 바로 쓸 수 있게 간결하고 정확하게 답하세요.\n"
    "2. 제공된 참고 자료만 근거로 답하세요. 자료에 없는 수치는 지어내지 마세요.\n"
    "3. 토크 값, 간격(clearance), 교체 주기 등 수치와 단위는 정확히 인용하세요.\n"
    "4. 답변 본문에 [매뉴얼 p.N] 또는 [정비이력 #N] 형식으로 출처를 표시하세요.\n"
    "5. 참고 자료에서 답을 찾을 수 없으면 '제공된 자료에서 해당 정보를 찾지 못했습니다.'라고 말하세요."
)


def _post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{config.OLLAMA_BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama API 오류 {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(
            "Ollama 서버에 연결할 수 없습니다. 먼저 `ollama serve`가 실행 중인지 확인하세요."
        ) from exc


def _embed_one(text: str) -> List[float]:
    try:
        resp = _post_json(
            "/api/embed",
            {"model": config.OLLAMA_EMBED_MODEL, "input": text},
        )
        embeddings = resp.get("embeddings")
        if embeddings:
            return embeddings[0]
    except RuntimeError:
        # Older Ollama versions expose /api/embeddings instead of /api/embed.
        pass

    resp = _post_json(
        "/api/embeddings",
        {"model": config.OLLAMA_EMBED_MODEL, "prompt": text},
    )
    embedding = resp.get("embedding")
    if not embedding:
        raise RuntimeError("Ollama 임베딩 응답에 embedding 값이 없습니다.")
    return embedding


def embed_texts(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """Embed documents or queries with the local Ollama embedding model."""
    return [_embed_one(text) for text in texts]


def embed_query(text: str) -> List[float]:
    return embed_texts([text], task_type="RETRIEVAL_QUERY")[0]


def generate_answer(query: str, context: str) -> str:
    prompt = (
        f"## 참고 자료\n{context}\n\n"
        f"## 기관사 질문\n{query}\n\n"
        "참고 자료만 근거로 답하고, 사용한 출처를 본문에 표시하세요."
    )
    resp = _post_json(
        "/api/chat",
        {
            "model": config.OLLAMA_CHAT_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0},
        },
    )
    message = resp.get("message") or {}
    text = message.get("content")
    return text.strip() if text else "(빈 응답)"
