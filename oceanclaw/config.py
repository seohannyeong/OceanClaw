"""환경설정 한 곳 모음. 값은 .env 파일이나 환경변수로 덮어쓸 수 있다."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv 미설치 시에도 동작
    pass


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INDEX_DIR = ROOT / "index"

# 입력 데이터 (샘플 또는 실제 파일 경로)
PDF_PATH = Path(os.getenv("PDF_PATH", str(DATA_DIR / "manual.pdf")))
CSV_PATH = Path(os.getenv("CSV_PATH", str(DATA_DIR / "maintenance_logs.csv")))

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# NOTE: 접근 가능한 모델명으로 .env에서 바꿔도 된다.
#   계획서 기준: 답변 gemini-3.1-flash / 임베딩 gemini-embedding-001
#   안전한 기본값으로 널리 쓰이는 모델을 둔다.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-004")

# 검색/청크 파라미터
TOP_K_PDF = int(os.getenv("TOP_K_PDF", "4"))
TOP_K_CSV = int(os.getenv("TOP_K_CSV", "5"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "700"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

# 인덱스 저장 위치
PDF_INDEX_PREFIX = str(INDEX_DIR / "pdf")
CSV_INDEX_PREFIX = str(INDEX_DIR / "csv")
