"""Gemini 클라이언트 래퍼: 임베딩 + 답변 생성."""

from __future__ import annotations

from typing import List

from . import config

_client = None


def get_client():
    """Gemini 클라이언트를 한 번만 만들어 재사용한다."""
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY 가 설정되지 않았습니다. "
                ".env 파일에 GEMINI_API_KEY=... 를 넣으세요. "
                "(키 발급: https://aistudio.google.com/apikey)"
            )
        from google import genai

        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def embed_texts(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """여러 텍스트를 임베딩한다. (배치 처리)"""
    from google.genai import types

    client = get_client()
    vectors: List[List[float]] = []
    batch = 100
    for i in range(0, len(texts), batch):
        chunk = texts[i : i + batch]
        resp = client.models.embed_content(
            model=config.EMBED_MODEL,
            contents=chunk,
            config=types.EmbedContentConfig(task_type=task_type),
        )
        vectors.extend([e.values for e in resp.embeddings])
    return vectors


def embed_query(text: str) -> List[float]:
    """검색 질의용 임베딩 (task_type=RETRIEVAL_QUERY)."""
    return embed_texts([text], task_type="RETRIEVAL_QUERY")[0]


SYSTEM_PROMPT = (
    "당신은 선박 기관실의 정비를 돕는 전문 AI 어시스턴트입니다.\n"
    "규칙:\n"
    "1. 반드시 한국어로, 기관사가 현장에서 바로 쓸 수 있게 간결하고 정확하게 답하세요.\n"
    "2. 아래 제공된 '참고 자료'에 있는 내용만 근거로 답하세요. 자료에 없는 수치를 지어내지 마세요.\n"
    "3. 토크 값, 간격(clearance), 교체 주기 등 수치는 단위와 함께 정확히 인용하세요.\n"
    "4. 답변 본문에서 근거가 된 부분에는 [매뉴얼 p.N] 또는 [정비이력 #N] 형식으로 출처를 표기하세요.\n"
    "5. 참고 자료에서 답을 찾을 수 없으면 솔직히 '제공된 자료에서 해당 정보를 찾지 못했습니다'라고 말하세요."
)


def generate_answer(query: str, context: str) -> str:
    """질문 + 컨텍스트로 한국어 답변을 생성한다."""
    from google.genai import types

    client = get_client()
    prompt = (
        f"## 참고 자료\n{context}\n\n"
        f"## 기관사 질문\n{query}\n\n"
        "위 참고 자료만 근거로 답하고, 사용한 출처를 본문에 표기하세요."
    )
    resp = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    return resp.text or "(빈 응답)"
