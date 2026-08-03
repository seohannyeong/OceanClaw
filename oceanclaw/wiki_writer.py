"""Generate Obsidian-compatible Wiki documents from retrieved evidence."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from . import config
from .answer import format_context, search_manual, search_sensor, unique_sources
from .ollama_chat import chat

WikiType = Literal["component", "procedure", "log"]

WIKI_SYSTEM_PROMPT = """You are OceanClaw, a ship maintenance Wiki writer.
Write Obsidian-compatible Markdown in Korean.
Use only the provided context.
Do not invent specifications, page numbers, event ids, warnings, or procedures.
If important information is missing, write "확인 필요".
Use Obsidian internal links with [[snake_case_document_name]] when linking related topics.
Always include a "## 출처" section.
"""

TYPE_TO_DIR = {
    "component": "components",
    "procedure": "procedures",
    "log": "logs",
}


def slugify(value: str) -> str:
    slug = value.lower()
    slug = re.sub(r"[^0-9a-zA-Z가-힣]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "wiki_document"


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
) -> Path:
    if output_path:
        return config.project_path(str(output_path))
    filename = f"{slugify(topic)}.md"
    return config.WIKI_DIR / TYPE_TO_DIR[wiki_type] / filename


def build_wiki_prompt(
    topic: str,
    wiki_type: WikiType,
    results: list[dict],
    sources: list[str],
) -> str:
    if wiki_type == "procedure":
        required_sections = """# 문서 제목

## 목적
## 관련 부품
## 작업 전 조건
## 절차
## 주의사항
## 관련 문서
## 출처"""
    elif wiki_type == "log":
        required_sections = """# 문서 제목

## 이벤트 요약
## 관련 장비
## 증상
## 권장 조치
## 관련 문서
## 출처"""
    else:
        required_sections = """# 문서 제목

## 개요
## 관련 절차
## 주요 점검 포인트
## 관련 문서
## 출처"""

    return f"""Topic:
{topic}

Wiki document type:
{wiki_type}

Required Markdown structure:
{required_sections}

Verified sources that must appear in "## 출처":
{chr(10).join(f"- {source}" for source in sources)}

Context:
{format_context(results)}
"""


def collect_wiki_evidence(topic: str, route: str, top_k: int) -> list[dict]:
    if route == "manual":
        return search_manual(topic, top_k)
    if route == "sensor":
        return search_sensor(topic, top_k)
    return search_manual(topic, top_k) + search_sensor(topic, top_k)


def generate_wiki_document(
    topic: str,
    route: str = "both",
    wiki_type: WikiType | None = None,
    top_k: int = 3,
    output_path: Path | None = None,
    overwrite: bool = False,
) -> dict:
    selected_type = wiki_type or infer_wiki_type(topic, route)
    path = resolve_output_path(topic, selected_type, output_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Wiki file already exists. Use --overwrite: {path}")

    results = collect_wiki_evidence(topic, route, top_k)
    if not results:
        raise ValueError(f"No evidence found for topic: {topic}")

    sources = unique_sources(results)
    prompt = build_wiki_prompt(topic, selected_type, results, sources)
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

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.strip() + "\n", encoding="utf-8")

    return {
        "topic": topic,
        "wiki_type": selected_type,
        "path": path,
        "sources": sources,
        "results": results,
    }
