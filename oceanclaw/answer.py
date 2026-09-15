"""Generate grounded answers from manual chunks, sensor events, and wiki notes."""

from __future__ import annotations

from time import perf_counter

from . import config
from .ollama_chat import chat
from .router import route_by_score
from .vectorstore import search_faiss_index

SYSTEM_PROMPT = """You are OceanClaw, a ship maintenance AI assistant.
Answer in Korean.
Use only the provided context.

Evidence priority rules:
- Prefer evidence that directly answers the user's question.
- For maintenance questions, prefer specific procedure sections such as "Maintenance Procedures", "Check", "Replace", "Drain", "Inspect", or a matching component/procedure title.
- Treat general descriptions, EPA requirements, environmental conditions, and background text as secondary unless they directly answer the question.
- If evidence appears to conflict, prioritize the more specific maintenance procedure over general background text and mention uncertainty briefly.

Safety and grounding rules:
- Do not invent values, procedures, warnings, events, causes, part names, or page numbers.
- Do not reverse safety conditions, prohibitions, engine running/stopped state, temperature conditions, numeric values, or units.
- Preserve safety warnings and important cautions.
- If the context does not contain enough information, say that the provided context is insufficient.

Answer style:
- Start with the direct answer first.
- When explaining procedures, use concise numbered steps.
- When explaining sensor events, mention component, severity, running hours, symptom, and recommended action if present.
- When using wiki notes, distinguish them from official manual evidence.
- Do not include a source section yourself. The program will attach verified sources.
"""


def search_manual(question: str, top_k: int = 3, profile: str = "titles",
                  min_score: float = 0.0, max_chars: int = 5000) -> list[dict]:
    if profile not in {"legacy", "titles", "titles_neighbors"}:
        raise ValueError("Unknown manual profile")
    if profile != "legacy":
        from .contextual_manual import search_contextual_manual
        return search_contextual_manual(question, top_k, profile == "titles_neighbors", min_score, max_chars)
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


def format_title_paths(title_paths: list) -> list[str]:
    """Return readable section paths for the LLM context."""
    formatted = []
    for path in title_paths or []:
        if isinstance(path, (list, tuple)):
            text = " > ".join(str(part) for part in path if part)
        else:
            text = str(path)
        if text and text not in formatted:
            formatted.append(text)
    return formatted


def format_score(value) -> str:
    return f"{value:.4f}" if isinstance(value, (int, float)) else "context"


def format_context(results: list[dict]) -> str:
    blocks = []
    for index, result in enumerate(results, start=1):
        if result.get("kind") == "sensor":
            doc = result["document"]
            lines = [
                f"[{index}] evidence_type: sensor_event",
                f"[{index}] retrieval_score: {format_score(result.get('score'))}",
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
                f"[{index}] evidence_type: wiki_note",
                f"[{index}] retrieval_score: {format_score(result.get('score'))}",
                f"[{index}] source: {result['source']}",
                f"[{index}] title: {doc.get('title')}",
                f"[{index}] wiki_type: {doc.get('wiki_type')}",
                f"[{index}] chunk_id: {result['chunk_id']}",
                f"[{index}] text:",
                str(result["text"]),
            ]
        else:
            section_titles = format_title_paths(result.get("title_paths"))
            lines = [
                f"[{index}] evidence_type: official_manual",
                f"[{index}] retrieval_score: {format_score(result.get('score'))}",
                f"[{index}] context_role: {result.get('context_role', 'seed')}",
                f"[{index}] source: {result['source']}",
                f"[{index}] page: {result['page']}",
                f"[{index}] chunk_id: {result['chunk_id']}",
                f"[{index}] section_titles:",
                *(f"- {title}" for title in section_titles),
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
    top_k: int = 3,
    min_score: float = 0.0,
    route_override: str | None = None,
    save_log: bool = False,
    manual_profile: str = "titles",
    max_context_chars: int = 5000,
) -> dict:
    started = perf_counter()
    if manual_profile not in {"legacy", "titles", "titles_neighbors"}:
        raise ValueError("Unknown manual profile")
    def manual_results_for_question():
        return search_manual(question, top_k, manual_profile, min_score, max_context_chars)

    if route_override == "manual":
        route = "manual"
        results = manual_results_for_question()
    elif route_override == "sensor":
        route = "sensor"
        results = search_sensor(question, top_k)
    elif route_override == "wiki":
        route = "wiki"
        results = search_wiki(question, top_k)
    elif route_override == "both":
        route = "both"
        results = manual_results_for_question() + search_sensor(question, top_k)
    elif route_override == "all":
        route = "all"
        results = (
            manual_results_for_question()
            + search_sensor(question, top_k)
            + search_wiki(question, top_k)
        )
    else:
        manual_results = manual_results_for_question()
        sensor_results = search_sensor(question, top_k)
        # Scores from different embedding models are not directly comparable.
        route = route_by_score(manual_results, sensor_results) if manual_profile == "legacy" else "both"
        if route == "manual":
            results = manual_results
        elif route == "sensor":
            results = sensor_results
        else:
            results = manual_results + sensor_results

    filtered_results = [result for result in results if result.get("context_role") == "neighbor" or result["score"] >= min_score]
    retrieval_seconds = perf_counter() - started
    expanded_query = results[0].get("expanded_query", question) if results else question

    if not filtered_results:
        return {
            "question": question,
            "route": route,
            "expanded_query": expanded_query,
            "answer": "검색된 근거가 부족해서 답변할 수 없습니다.",
            "sources": [],
            "results": results,
            "manual_profile": manual_profile,
            "timing": {"retrieval_seconds": retrieval_seconds, "generation_seconds": 0,
                       "total_seconds": perf_counter() - started},
            "context_chars": 0,
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
        "manual_profile": manual_profile,
        "timing": {"retrieval_seconds": retrieval_seconds, "generation_seconds": perf_counter() - started - retrieval_seconds,
                   "total_seconds": perf_counter() - started},
        "context_chars": sum(len(r["text"]) for r in filtered_results),
    }

    if save_log:
        from .wiki_log import save_answer_log

        result["wiki_log_path"] = str(save_answer_log(result))

    return result
