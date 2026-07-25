"""Project paths and settings."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_DIR = ROOT / "index"


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


PDF_PATH = project_path(
    os.getenv("PDF_PATH", "data/raw/yanmar_6lf_operation_manual.pdf")
)
PDF_PAGES_PATH = project_path(
    os.getenv("PDF_PAGES_PATH", "data/interim/pdf_pages.jsonl")
)
PDF_CHUNKS_PATH = project_path(
    os.getenv("PDF_CHUNKS_PATH", "data/processed/pdf_chunks.jsonl")
)

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "gemma3:4b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

PDF_FAISS_PATH = project_path(os.getenv("PDF_FAISS_PATH", "index/pdf.faiss"))
PDF_DOCS_PATH = project_path(os.getenv("PDF_DOCS_PATH", "index/pdf_docs.json"))

SENSOR_EVENTS_PATH = project_path(
    os.getenv("SENSOR_EVENTS_PATH", "data/processed/sensor_events.csv")
)
SENSOR_FAISS_PATH = project_path(os.getenv("SENSOR_FAISS_PATH", "index/sensor.faiss"))
SENSOR_DOCS_PATH = project_path(os.getenv("SENSOR_DOCS_PATH", "index/sensor_docs.json"))
