"""FastAPI server for OceanClaw RAG."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.parse import parse_qs
from urllib.request import Request as UrlRequest, urlopen
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config
from .answer import answer_question, search_manual, search_sensor, search_wiki
from .ollama_embed import check_ollama
from .wiki_writer import generate_wiki_document

Route = Literal["manual", "sensor", "wiki", "both", "all"]
WikiType = Literal["component", "procedure", "log"]

app = FastAPI(
    title="OceanClaw API",
    description="Offline-first ship maintenance RAG API using Ollama and FAISS.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=config.ROOT / "static"), name="static")


class AskRequest(BaseModel):
    manual_profile: Literal["legacy", "titles", "titles_neighbors"] = "titles"
    max_context_chars: int = Field(5000, ge=1000, le=12000)
    question: str = Field(..., min_length=1, examples=["엔진 오일 점검 방법 알려줘"])
    top_k: int = Field(3, ge=1, le=10)
    min_score: float = Field(0.0, ge=0.0, le=1.0)
    save_log: bool = Field(False, description="답변 결과를 wiki/logs Markdown 파일로 저장")
    route: Route | None = Field(
        None,
        description="manual, sensor, wiki, both, all 중 하나로 검색 경로를 고정",
    )


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["engine oil level check dipstick"])
    top_k: int = Field(3, ge=1, le=10)


class WikiNoteRequest(BaseModel):
    topic: str = Field(..., min_length=1, examples=["엔진 오일 점검"])
    route: Route = Field("all", description="Wiki 문서 생성 전에 검색할 근거 범위")
    wiki_type: WikiType | None = Field(
        None,
        description="component, procedure, log 중 하나. 비워두면 topic을 기준으로 자동 추정",
    )
    top_k: int = Field(3, ge=1, le=10)
    min_score: float = Field(0.0, ge=0.0, le=1.0)
    filename: str | None = Field(
        None,
        description="저장할 Markdown 파일명. 비워두면 topic 기반으로 자동 생성",
    )
    overwrite: bool = Field(False, description="같은 파일명이 있으면 덮어쓰기")
    auto_rename: bool = Field(True, description="같은 파일명이 있으면 시간값을 붙여 새 파일로 저장")
    rebuild_index: bool = Field(
        False,
        description="문서 저장 후 Wiki FAISS index를 즉시 다시 생성",
    )


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the OceanClaw web UI."""
    return FileResponse(config.ROOT / "static" / "index.html")


@app.get("/health")
def health() -> dict:
    """Check whether the API and Ollama endpoint are reachable."""
    check_ollama(config.OLLAMA_BASE_URL, config.OLLAMA_TIMEOUT)
    return {
        "status": "ok",
        "ollama_base_url": config.OLLAMA_BASE_URL,
        "chat_model": config.OLLAMA_CHAT_MODEL,
        "embed_model": config.OLLAMA_EMBED_MODEL,
        "manual_embed_model": "bge-m3",
        "manual_profile": "titles",
    }


@app.post("/ask")
def ask(request: AskRequest) -> dict:
    """Generate a grounded answer from manual and/or sensor retrieval."""
    return answer_question(
        question=request.question,
        top_k=request.top_k,
        min_score=request.min_score,
        route_override=request.route,
        save_log=request.save_log,
        manual_profile=request.manual_profile,
        max_context_chars=request.max_context_chars,
    )


@app.post("/search/manual")
def search_manual_endpoint(request: SearchRequest) -> dict:
    """Search the PDF manual index only."""
    return {
        "query": request.query,
        "results": search_manual(request.query, request.top_k),
    }


@app.post("/search/sensor")
def search_sensor_endpoint(request: SearchRequest) -> dict:
    """Search the sensor event index only."""
    return {
        "query": request.query,
        "results": search_sensor(request.query, request.top_k),
    }


@app.post("/search/wiki")
def search_wiki_endpoint(request: SearchRequest) -> dict:
    """Search the Obsidian Wiki index only."""
    return {
        "query": request.query,
        "results": search_wiki(request.query, request.top_k),
    }


@app.post("/wiki/notes")
def create_wiki_note(request: WikiNoteRequest) -> dict:
    """Create an Obsidian Wiki Markdown note from retrieved RAG evidence."""
    try:
        result = generate_wiki_document(
            topic=request.topic,
            route=request.route,
            wiki_type=request.wiki_type,
            top_k=request.top_k,
            min_score=request.min_score,
            filename=request.filename,
            overwrite=request.overwrite,
            auto_rename=request.auto_rename,
            rebuild_index=request.rebuild_index,
        )
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "topic": result["topic"],
        "wiki_type": result["wiki_type"],
        "route": result["route"],
        "path": str(result["path"]),
        "sources": result["sources"],
        "result_count": len(result["results"]),
        "index": {
            key: str(value) if key.endswith("_path") else value
            for key, value in result["index"].items()
        }
        if result.get("index")
        else None,
    }


def format_mattermost_answer(result: dict) -> str:
    """Format an OceanClaw answer for a Mattermost slash command response."""
    sources = result.get("sources", [])
    source_text = "\n".join(f"- {source}" for source in sources) or "- 없음"
    log_line = ""
    if result.get("wiki_log_path"):
        log_line = f"\n\n**Wiki 로그**\n`{result['wiki_log_path']}`"

    return (
        f"### OceanClaw 답변\n\n"
        f"**질문**\n{result['question']}\n\n"
        f"**검색 경로**\n`{result['route']}`\n\n"
        f"**답변**\n{result['answer']}\n\n"
        f"**출처**\n{source_text}"
        f"{log_line}"
    )


def format_mattermost_wiki_note(result: dict) -> str:
    """Format a generated Wiki note result for Mattermost."""
    source_text = "\n".join(f"- {source}" for source in result.get("sources", [])) or "- 없음"
    index_text = ""
    if result.get("index"):
        index = result["index"]
        index_text = (
            "\n\n**Wiki index**\n"
            f"- chunks: {index['chunk_count']}\n"
            f"- indexed: {index['indexed_count']}"
        )

    return (
        "### OceanClaw Wiki 문서 생성 완료\n\n"
        f"**주제**\n{result['topic']}\n\n"
        f"**문서 유형**\n`{result['wiki_type']}`\n\n"
        f"**검색 경로**\n`{result['route']}`\n\n"
        f"**저장 위치**\n`{result['path']}`\n\n"
        f"**출처**\n{source_text}"
        f"{index_text}"
    )


def post_mattermost_response(response_url: str, payload: dict) -> None:
    """Post a delayed slash command response back to Mattermost."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = UrlRequest(
        response_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10):
            pass
    except URLError as exc:
        print(f"[mattermost] failed to post delayed response: {exc}")


def generate_and_post_mattermost_answer(question: str, response_url: str) -> None:
    """Generate the RAG answer outside the slash command timeout window."""
    try:
        result = answer_question(
            question=question,
            top_k=config.MATTERMOST_TOP_K,
            route_override=config.MATTERMOST_DEFAULT_ROUTE,
            save_log=config.MATTERMOST_SAVE_LOG,
        )
        text = format_mattermost_answer(result)
    except Exception as exc:  # pragma: no cover - defensive boundary for chat UX
        text = (
            "### OceanClaw 오류\n\n"
            "답변 생성 중 문제가 발생했습니다.\n\n"
            f"`{type(exc).__name__}: {exc}`"
        )

    post_mattermost_response(
        response_url,
        {
            "response_type": config.MATTERMOST_RESPONSE_TYPE,
            "username": "OceanClaw",
            "text": text,
        },
    )


def generate_and_post_mattermost_wiki_note(topic: str, response_url: str) -> None:
    """Generate a Wiki note outside the slash command timeout window."""
    try:
        result = generate_wiki_document(
            topic=topic,
            route=config.MATTERMOST_WIKI_NOTE_ROUTE,
            top_k=config.MATTERMOST_WIKI_NOTE_TOP_K,
            auto_rename=True,
            rebuild_index=config.MATTERMOST_WIKI_NOTE_REBUILD_INDEX,
        )
        text = format_mattermost_wiki_note(result)
    except Exception as exc:  # pragma: no cover - defensive boundary for chat UX
        text = (
            "### OceanClaw Wiki 문서 생성 오류\n\n"
            "Wiki 문서를 생성하는 중 문제가 발생했습니다.\n\n"
            f"`{type(exc).__name__}: {exc}`"
        )

    post_mattermost_response(
        response_url,
        {
            "response_type": config.MATTERMOST_RESPONSE_TYPE,
            "username": "OceanClaw",
            "text": text,
        },
    )


@app.post("/mattermost/slash")
async def mattermost_slash(request: Request, background_tasks: BackgroundTasks) -> dict:
    """Handle Mattermost custom slash command requests."""
    body = (await request.body()).decode("utf-8")
    form = {key: values[0] for key, values in parse_qs(body).items()}

    expected_token = config.MATTERMOST_SLASH_TOKEN
    if expected_token and form.get("token") != expected_token:
        raise HTTPException(status_code=403, detail="Invalid Mattermost token")

    question = form.get("text", "").strip()
    if not question:
        return {
            "response_type": "ephemeral",
            "text": "질문을 입력해주세요. 예: `/oceanclaw 엔진 오일 점검 방법 알려줘`",
        }

    response_url = form.get("response_url", "")
    if response_url:
        background_tasks.add_task(
            generate_and_post_mattermost_answer,
            question,
            response_url,
        )
        return {
            "response_type": "ephemeral",
            "text": f"OceanClaw가 답변을 생성 중입니다.\n\n**질문**\n{question}",
        }

    result = answer_question(
        question=question,
        top_k=config.MATTERMOST_TOP_K,
        route_override=config.MATTERMOST_DEFAULT_ROUTE,
        save_log=config.MATTERMOST_SAVE_LOG,
    )

    return {
        "response_type": config.MATTERMOST_RESPONSE_TYPE,
        "username": "OceanClaw",
        "text": format_mattermost_answer(result),
    }


@app.post("/mattermost/wiki-note")
async def mattermost_wiki_note(request: Request, background_tasks: BackgroundTasks) -> dict:
    """Handle Mattermost slash command requests for Wiki note generation."""
    body = (await request.body()).decode("utf-8")
    form = {key: values[0] for key, values in parse_qs(body).items()}

    expected_token = config.MATTERMOST_SLASH_TOKEN
    if expected_token and form.get("token") != expected_token:
        raise HTTPException(status_code=403, detail="Invalid Mattermost token")

    topic = form.get("text", "").strip()
    if not topic:
        return {
            "response_type": "ephemeral",
            "text": "생성할 Wiki 문서 주제를 입력해주세요. 예: `/oceanclaw-note 엔진 오일 점검`",
        }

    response_url = form.get("response_url", "")
    if response_url:
        background_tasks.add_task(
            generate_and_post_mattermost_wiki_note,
            topic,
            response_url,
        )
        return {
            "response_type": "ephemeral",
            "text": f"OceanClaw가 Wiki 문서를 생성 중입니다.\n\n**주제**\n{topic}",
        }

    result = generate_wiki_document(
        topic=topic,
        route=config.MATTERMOST_WIKI_NOTE_ROUTE,
        top_k=config.MATTERMOST_WIKI_NOTE_TOP_K,
        auto_rename=True,
        rebuild_index=config.MATTERMOST_WIKI_NOTE_REBUILD_INDEX,
    )

    return {
        "response_type": config.MATTERMOST_RESPONSE_TYPE,
        "username": "OceanClaw",
        "text": format_mattermost_wiki_note(result),
    }
