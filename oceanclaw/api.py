"""FastAPI server for OceanClaw RAG."""

from __future__ import annotations

from urllib.parse import parse_qs
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from . import config
from .answer import answer_question, search_manual, search_sensor, search_wiki
from .ollama_embed import check_ollama

Route = Literal["manual", "sensor", "wiki", "both", "all"]

app = FastAPI(
    title="OceanClaw API",
    description="Offline-first ship maintenance RAG API using Ollama and FAISS.",
    version="0.1.0",
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["엔진 오일 점검 방법 알려줘"])
    top_k: int = Field(4, ge=1, le=10)
    min_score: float = Field(0.0, ge=0.0, le=1.0)
    save_log: bool = Field(False, description="답변 결과를 wiki/logs Markdown 파일로 저장")
    route: Route | None = Field(
        None,
        description="manual, sensor, wiki, both, all 중 하나로 검색 경로를 고정",
    )


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["engine oil level check dipstick"])
    top_k: int = Field(3, ge=1, le=10)


@app.get("/health")
def health() -> dict:
    """Check whether the API and Ollama endpoint are reachable."""
    check_ollama(config.OLLAMA_BASE_URL, config.OLLAMA_TIMEOUT)
    return {
        "status": "ok",
        "ollama_base_url": config.OLLAMA_BASE_URL,
        "chat_model": config.OLLAMA_CHAT_MODEL,
        "embed_model": config.OLLAMA_EMBED_MODEL,
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


@app.post("/mattermost/slash")
async def mattermost_slash(request: Request) -> dict:
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
