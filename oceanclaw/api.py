"""FastAPI server for OceanClaw RAG."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from . import config
from .answer import answer_question, search_manual, search_sensor
from .ollama_embed import check_ollama

Route = Literal["manual", "sensor", "both"]

app = FastAPI(
    title="OceanClaw API",
    description="Offline-first ship maintenance RAG API using Ollama and FAISS.",
    version="0.1.0",
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["엔진 오일 점검 방법 알려줘"])
    top_k: int = Field(4, ge=1, le=10)
    min_score: float = Field(0.0, ge=0.0, le=1.0)
    route: Route | None = Field(
        None,
        description="manual, sensor, both 중 하나로 검색 경로를 고정",
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
