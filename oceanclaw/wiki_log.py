"""Save OceanClaw answers as Obsidian-compatible Markdown logs."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

from . import config
from .wiki_writer import slugify


def _now() -> datetime:
    return datetime.now(timezone(timedelta(hours=9), "KST"))


def _result_summary(result: dict) -> str:
    kind = result.get("kind", "manual")
    score = float(result.get("score", 0.0))

    if kind == "sensor":
        doc = result.get("document", {})
        return (
            f"- sensor | score={score:.4f} | "
            f"event_id={doc.get('event_id')} | "
            f"component={doc.get('component')} | "
            f"severity={doc.get('severity')}"
        )
    if kind == "wiki":
        doc = result.get("document", {})
        return (
            f"- wiki | score={score:.4f} | "
            f"source={result.get('source')} | "
            f"title={doc.get('title')} | "
            f"type={doc.get('wiki_type')}"
        )
    return (
        f"- manual | score={score:.4f} | "
        f"source={result.get('source')} | "
        f"page={result.get('page')} | "
        f"chunk_id={result.get('chunk_id')}"
    )


def _markdown(result: dict, created_at: datetime) -> str:
    sources = result.get("sources", [])
    search_results = result.get("results", [])
    question = str(result.get("question", "")).strip()
    answer = str(result.get("answer", "")).strip()

    source_lines = "\n".join(f"- {source}" for source in sources) or "- 없음"
    result_lines = "\n".join(_result_summary(item) for item in search_results) or "- 없음"

    return f"""# {question}

## 질문
{question}

## 답변
{answer}

## 출처
{source_lines}

## 검색 정보
- route: {result.get("route")}
- expanded_query: {result.get("expanded_query")}
- created_at: {created_at.strftime("%Y-%m-%d %H:%M:%S %Z")}

## 검색 결과 요약
{result_lines}
"""


def save_answer_log(result: dict, logs_dir: Path | None = None) -> Path:
    """Write a single answer result to wiki/logs and return the saved path."""
    created_at = _now()
    target_dir = logs_dir or config.WIKI_DIR / "logs"
    target_dir.mkdir(parents=True, exist_ok=True)

    question = str(result.get("question", "answer")).strip()
    date_prefix = created_at.strftime("%Y-%m-%d_%H%M%S")
    filename = f"{date_prefix}_{slugify(question)[:60]}.md"
    path = target_dir / filename
    path.write_text(_markdown(result, created_at), encoding="utf-8", newline="\n")
    return path
