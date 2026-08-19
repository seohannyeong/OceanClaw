"""Generate grounded answers from manual chunks, sensor events, and wiki notes."""

from __future__ import annotations

from . import config
from .ollama_chat import chat
from .router import route_by_score
from .vectorstore import search_faiss_index

SYSTEM_PROMPT = """You are OceanClaw, a ship maintenance AI assistant.
Answer in Korean.
Use only the provided context.
Do not invent values, procedures, warnings, events, or page numbers.
If the context does not contain enough information, say that the provided context is insufficient.
Preserve safety warnings and important cautions.
When explaining procedures, use concise numbered steps.
When explaining sensor events, mention component, severity, running hours, symptom, and recommended action if present.
When using wiki notes, distinguish them from official manual evidence.
Do not include a source section yourself. The program will attach verified sources.
"""


def search_manual(question: str, top_k: int) -> list[dict]:
    results = search_faiss_index(
        query=question,
        faiss_path=config.PDF_FAISS_PATH,
        docs_path=config.PDF_DOCS_PATH,
        model=config.OLLAMA_EMBED_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        timeout=config.OLLAMA_TIMEOUT,
        top_k=top_k,
    )
    for result in results:
        result["kind"] = "manual"
    return results


def search_sensor(question: str, top_k: int) -> list[dict]:
    results = search_faiss_index(
        query=question,
        faiss_path=config.SENSOR_FAISS_PATH,
        docs_path=config.SENSOR_DOCS_PATH,
        model=config.OLLAMA_EMBED_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        timeout=config.OLLAMA_TIMEOUT,
        top_k=top_k,
    )
    for result in results:
        result["kind"] = "sensor"
    return results


def search_wiki(question: str, top_k: int) -> list[dict]:
    results = search_faiss_index(
        query=question,
        faiss_path=config.WIKI_FAISS_PATH,
        docs_path=config.WIKI_DOCS_PATH,
        model=config.OLLAMA_EMBED_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        timeout=config.OLLAMA_TIMEOUT,
        top_k=top_k,
    )
    for result in results:
        result["kind"] = "wiki"
    return results


def format_context(results: list[dict]) -> str:
    blocks = []
    for index, result in enumerate(results, start=1):
        if result.get("kind") == "sensor":
            doc = result["document"]
            lines = [
                f"[{index}] kind: sensor",
                f"[{index}] event_id: {doc.get('event_id')}",
                f"[{index}] component: {doc.get('component')}",
                f"[{index}] severity: {doc.get('severity')}",
                f"[{index}] running_hours: {doc.get('running_hours')}",
                f"[{index}] status: {doc.get('status')}",
                f"[{index}] text:",
                str(result["text"]),
            ]
        elif result.get("kind") == "wiki":
            doc = result["document"]
            lines = [
                f"[{index}] kind: wiki",
                f"[{index}] source: {result['source']}",
                f"[{index}] title: {doc.get('title')}",
                f"[{index}] wiki_type: {doc.get('wiki_type')}",
                f"[{index}] chunk_id: {result['chunk_id']}",
                f"[{index}] text:",
                str(result["text"]),
            ]
        else:
            lines = [
                f"[{index}] kind: manual",
                f"[{index}] source: {result['source']}",
                f"[{index}] page: {result['page']}",
                f"[{index}] chunk_id: {result['chunk_id']}",
                f"[{index}] text:",
                str(result["text"]),
            ]
        blocks.append("\n".join(lines))
    return "\n\n---\n\n".join(blocks)


def unique_sources(results: list[dict]) -> list[str]:
    seen = set()
    sources = []
    for result in results:
        if result.get("kind") == "sensor":
            doc = result["document"]
            label = (
                f"sensor event {doc.get('event_id')} "
                f"({doc.get('component')}, {doc.get('severity')})"
            )
        elif result.get("kind") == "wiki":
            doc = result["document"]
            label = f"{result['source']} ({doc.get('title')})"
        else:
            label = f"{result['source']} p.{result['page']}"

        if label not in seen:
            sources.append(label)
            seen.add(label)
    return sources


def answer_question(
    question: str,
    top_k: int = 4,
    min_score: float = 0.0,
    route_override: str | None = None,
    save_log: bool = False,
) -> dict:
    if route_override == "manual":
        route = "manual"
        results = search_manual(question, top_k)
    elif route_override == "sensor":
        route = "sensor"
        results = search_sensor(question, top_k)
    elif route_override == "wiki":
        route = "wiki"
        results = search_wiki(question, top_k)
    elif route_override == "both":
        route = "both"
        results = search_manual(question, top_k) + search_sensor(question, top_k)
    elif route_override == "all":
        route = "all"
        results = (
            search_manual(question, top_k)
            + search_sensor(question, top_k)
            + search_wiki(question, top_k)
        )
    else:
        manual_results = search_manual(question, top_k)
        sensor_results = search_sensor(question, top_k)
        route = route_by_score(manual_results, sensor_results)
        if route == "manual":
            results = manual_results
        elif route == "sensor":
            results = sensor_results
        else:
            results = manual_results + sensor_results

    filtered_results = [result for result in results if result["score"] >= min_score]
    expanded_query = results[0].get("expanded_query", question) if results else question

    if not filtered_results:
        return {
            "question": question,
            "route": route,
            "expanded_query": expanded_query,
            "answer": "검색된 근거가 부족해서 답변할 수 없습니다.",
            "sources": [],
            "results": results,
        }

    user_prompt = f"""Question:
{question}

Expanded search query:
{expanded_query}

Retrieval route:
{route}

Context:
{format_context(filtered_results)}
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

    result = {
        "question": question,
        "route": route,
        "expanded_query": expanded_query,
        "answer": content,
        "sources": unique_sources(filtered_results),
        "results": filtered_results,
    }

    if save_log:
        from .wiki_log import save_answer_log

        result["wiki_log_path"] = str(save_answer_log(result))

    return result
