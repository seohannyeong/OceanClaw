"""Generate grounded answers from retrieved PDF chunks."""

from __future__ import annotations

from . import config
from .ollama_chat import chat
from .vectorstore import search_faiss_index


SYSTEM_PROMPT = """You are OceanClaw, a ship maintenance AI assistant.
Answer in Korean.
Use only the provided context.
Do not invent values, procedures, warnings, or page numbers.
If the context does not contain enough information, say that the manual context is insufficient.
Preserve safety warnings and important cautions.
When explaining procedures, use concise numbered steps.
Do not include a source section yourself. The program will attach verified sources.
"""


def format_context(results: list[dict]) -> str:
    blocks = []
    for index, result in enumerate(results, start=1):
        blocks.append(
            "\n".join(
                [
                    f"[{index}] source: {result['source']}",
                    f"[{index}] page: {result['page']}",
                    f"[{index}] chunk_id: {result['chunk_id']}",
                    f"[{index}] text:",
                    str(result["text"]),
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def unique_sources(results: list[dict]) -> list[str]:
    seen = set()
    sources = []
    for result in results:
        label = f"{result['source']} p.{result['page']}"
        if label not in seen:
            sources.append(label)
            seen.add(label)
    return sources


def answer_question(
    question: str,
    top_k: int = 4,
    min_score: float = 0.0,
) -> dict:
    results = search_faiss_index(
        query=question,
        faiss_path=config.PDF_FAISS_PATH,
        docs_path=config.PDF_DOCS_PATH,
        model=config.OLLAMA_EMBED_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        timeout=config.OLLAMA_TIMEOUT,
        top_k=top_k,
    )

    filtered_results = [result for result in results if result["score"] >= min_score]
    context = format_context(filtered_results)
    expanded_query = results[0].get("expanded_query", question) if results else question

    if not filtered_results:
        return {
            "question": question,
            "expanded_query": expanded_query,
            "answer": "검색된 매뉴얼 근거가 부족해서 답변할 수 없습니다.",
            "sources": [],
            "results": results,
        }

    user_prompt = f"""Question:
{question}

Expanded search query:
{expanded_query}

Context:
{context}
"""

    content = chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        model=config.OLLAMA_CHAT_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        timeout=config.OLLAMA_TIMEOUT,
    )

    return {
        "question": question,
        "expanded_query": expanded_query,
        "answer": content,
        "sources": unique_sources(filtered_results),
        "results": filtered_results,
    }
