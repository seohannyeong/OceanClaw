#!/usr/bin/env python3
"""Build a FAISS index for Obsidian Wiki Markdown documents."""

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
from oceanclaw.wiki_index import build_wiki_chunks

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Wiki FAISS index.")
    parser.add_argument("--wiki-dir", type=Path, default=config.WIKI_DIR)
    parser.add_argument("--chunks", type=Path, default=config.WIKI_CHUNKS_PATH)
    parser.add_argument("--faiss", type=Path, default=config.WIKI_FAISS_PATH)
    parser.add_argument("--docs", type=Path, default=config.WIKI_DOCS_PATH)
    parser.add_argument("--size", type=int, default=config.CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=config.CHUNK_OVERLAP)
    args = parser.parse_args()

    wiki_dir = config.project_path(str(args.wiki_dir))
    chunks_path = config.project_path(str(args.chunks))
    faiss_path = config.project_path(str(args.faiss))
    docs_path = config.project_path(str(args.docs))

    chunk_count = build_wiki_chunks(
        wiki_dir=wiki_dir,
        output_path=chunks_path,
        chunk_size=args.size,
        chunk_overlap=args.overlap,
    )
    print(f"[OK] created {chunk_count} wiki chunks")
    print(f"Chunks: {chunks_path}")

    check_ollama(config.OLLAMA_BASE_URL, config.OLLAMA_TIMEOUT)
    indexed_count = build_faiss_index(
        chunks_path=chunks_path,
        faiss_path=faiss_path,
        docs_path=docs_path,
        model=config.OLLAMA_EMBED_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        timeout=config.OLLAMA_TIMEOUT,
    )

    print(f"[OK] indexed {indexed_count} wiki chunks")
    print(f"FAISS: {faiss_path}")
    print(f"Docs: {docs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
