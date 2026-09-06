"""Generate Obsidian-compatible Wiki documents from retrieved evidence."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from . import config
from .answer import (
    format_context,
    search_manual,
    search_sensor,
    search_wiki,
    unique_sources,
)
from .ollama_chat import chat

WikiType = Literal["component", "procedure", "log"]
WikiRoute = Literal["manual", "sensor", "wiki", "both", "all"]

WIKI_SYSTEM_PROMPT = """You are OceanClaw, a ship maintenance Wiki writer.
Write Obsidian-compatible Markdown in Korean.
Use only the provided context.
Do not invent specifications, page numbers, event ids, warnings, or procedures.
If important information is missing, write "확인 필요".
Preserve important safety warnings.
Distinguish official manual evidence from wiki notes and sensor events.
Use Obsidian internal links with [[snake_case_document_name]] when linking related topics.
Do not wrap the answer in a code block.
"""

TYPE_TO_DIR = {
    "component": "components",
    "procedure": "procedures",
    "log": "logs",
}


def slugify(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[\\/:*?\"<>|]+", " ", slug)
    slug = re.sub(r"[^0-9a-zA-Z가-힣]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:80] or "wiki_document"


def infer_wiki_type(topic: str, route: str | None) -> WikiType:
    normalized = topic.lower()
    if route == "sensor":
        return "log"
    if any(word in normalized for word in ["event", "warning", "sensor", "fault", "alarm"]):
        return "log"
    if any(word in normalized for word in ["점검", "교체", "절차", "방법", "check", "replace", "procedure"]):
        return "procedure"
    return "component"


def resolve_output_path(
    topic: str,
    wiki_type: WikiType,
    output_path: Path | None = None,
    output_dir: Path | None = None,
    filename: str | None = None,
) -> Path:
    if output_path:
        return config.project_path(str(output_path))

    base_dir = config.project_path(str(output_dir)) if output_dir else config.WIKI_DIR / TYPE_TO_DIR[wiki_type]
    note_filename = filename or f"{slugify(topic)}.md"
    if not note_filename.endswith(".md"):
        note_filename += ".md"
    return base_dir / note_filename


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.stem}_{timestamp}{path.suffix}")


def collect_wiki_evidence(topic: str, route: WikiRoute, top_k: int) -> list[dict]:
    if route == "manual":
        return search_manual(topic, top_k)
    if route == "sensor":
        return search_sensor(topic, top_k)
    if route == "wiki":
        return search_wiki(topic, top_k)
    if route == "both":
        return search_manual(topic, top_k) + search_sensor(topic, top_k)
    return search_manual(topic, top_k) + search_sensor(topic, top_k) + search_wiki(topic, top_k)


def render_sources(sources: list[str]) -> str:
    return "\n".join(f"- {source}" for source in sources) or "- 확인 필요"


def build_wiki_prompt(
    topic: str,
    wiki_type: WikiType,
    route: WikiRoute,
    results: list[dict],
    sources: list[str],
) -> str:
    if wiki_type == "procedure":
        required_sections = """# 문서 제목

## 개요
## 관련 부품/데이터
## 작업 전 확인사항
## 점검 절차
## 주의사항
## 관련 센서 이상 징후
## 추가 확인 필요
## 출처"""
    elif wiki_type == "log":
        required_sections = """# 문서 제목

## 이벤트 요약
## 관련 장비
## 증상
## 권장 조치
## 관련 문서
## 추가 확인 필요
## 출처"""
    else:
        required_sections = """# 문서 제목

## 개요
## 관련 절차
## 주요 점검 포인트
## 관련 문서
## 추가 확인 필요
## 출처"""

    return f"""Topic:
{topic}

Wiki document type:
{wiki_type}

Retrieval route:
{route}

Required Markdown structure:
{required_sections}

Verified sources that must appear in "## 출처":
{render_sources(sources)}

Context:
{format_context(results)}
"""


def add_metadata(markdown: str, topic: str, route: WikiRoute, wiki_type: WikiType, sources: list[str]) -> str:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""---
type: {wiki_type}
created_at: {created_at}
created_by: OceanClaw
topic: {topic}
route: {route}
---

{markdown.strip()}

---

## 생성 정보

- 생성 시각: {created_at}
- 검색 경로: `{route}`

## 검색 근거

{render_sources(sources)}
"""


def rebuild_wiki_index() -> dict:
    from .vectorstore import build_faiss_index
    from .wiki_index import build_wiki_chunks

    chunk_count = build_wiki_chunks(
        wiki_dir=config.WIKI_DIR,
        output_path=config.WIKI_CHUNKS_PATH,
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )
    indexed_count = build_faiss_index(
        chunks_path=config.WIKI_CHUNKS_PATH,
        faiss_path=config.WIKI_FAISS_PATH,
        docs_path=config.WIKI_DOCS_PATH,
        model=config.OLLAMA_EMBED_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        timeout=config.OLLAMA_TIMEOUT,
    )
    return {
        "chunk_count": chunk_count,
        "indexed_count": indexed_count,
        "chunks_path": config.WIKI_CHUNKS_PATH,
        "faiss_path": config.WIKI_FAISS_PATH,
        "docs_path": config.WIKI_DOCS_PATH,
    }


def generate_wiki_document(
    topic: str,
    route: WikiRoute = "all",
    wiki_type: WikiType | None = None,
    top_k: int = 3,
    min_score: float = 0.0,
    output_path: Path | None = None,
    output_dir: Path | None = None,
    filename: str | None = None,
    overwrite: bool = False,
    auto_rename: bool = False,
    rebuild_index: bool = False,
) -> dict:
    selected_type = wiki_type or infer_wiki_type(topic, route)
    path = resolve_output_path(topic, selected_type, output_path, output_dir, filename)
    path = path if overwrite or not auto_rename else unique_path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Wiki file already exists. Use overwrite or auto_rename: {path}")

    results = collect_wiki_evidence(topic, route, top_k)
    filtered_results = [result for result in results if result["score"] >= min_score]
    if not filtered_results:
        raise ValueError(f"No evidence found for topic: {topic}")

    sources = unique_sources(filtered_results)
    prompt = build_wiki_prompt(topic, selected_type, route, filtered_results, sources)
    markdown = chat(
        messages=[
            {"role": "system", "content": WIKI_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        model=config.OLLAMA_CHAT_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        timeout=config.OLLAMA_TIMEOUT,
        temperature=0.1,
    )
    markdown = add_metadata(markdown, topic, route, selected_type, sources)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.strip() + "\n", encoding="utf-8", newline="\n")

    index_result = rebuild_wiki_index() if rebuild_index else None
    return {
        "topic": topic,
        "wiki_type": selected_type,
        "route": route,
        "path": path,
        "sources": sources,
        "results": filtered_results,
        "index": index_result,
    }
