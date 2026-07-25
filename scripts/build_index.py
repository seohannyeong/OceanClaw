#!/usr/bin/env python3
"""Build FAISS index from PDF chunks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config
from oceanclaw.ollama_embed import check_ollama
from oceanclaw.vectorstore import build_faiss_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PDF FAISS index.")
    parser.add_argument("--chunks", type=Path, default=config.PDF_CHUNKS_PATH)
    parser.add_argument("--faiss", type=Path, default=config.PDF_FAISS_PATH)
    parser.add_argument("--docs", type=Path, default=config.PDF_DOCS_PATH)
    parser.add_argument("--model", default=config.OLLAMA_EMBED_MODEL)
    parser.add_argument("--ollama-url", default=config.OLLAMA_BASE_URL)
    parser.add_argument("--timeout", type=int, default=config.OLLAMA_TIMEOUT)
    args = parser.parse_args()

    chunks_path = config.project_path(str(args.chunks))
    faiss_path = config.project_path(str(args.faiss))
    docs_path = config.project_path(str(args.docs))

    check_ollama(args.ollama_url, args.timeout)
    count = build_faiss_index(
        chunks_path=chunks_path,
        faiss_path=faiss_path,
        docs_path=docs_path,
        model=args.model,
        base_url=args.ollama_url,
        timeout=args.timeout,
    )

    print(f"[OK] indexed {count} chunks")
    print(f"FAISS: {faiss_path}")
    print(f"Docs: {docs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
