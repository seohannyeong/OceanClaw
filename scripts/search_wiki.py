#!/usr/bin/env python3
"""Search the Obsidian Wiki FAISS index."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config
from oceanclaw.ollama_embed import check_ollama
from oceanclaw.vectorstore import search_faiss_index

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Wiki FAISS index.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    check_ollama(config.OLLAMA_BASE_URL, config.OLLAMA_TIMEOUT)
    results = search_faiss_index(
        query=args.query,
        faiss_path=config.WIKI_FAISS_PATH,
        docs_path=config.WIKI_DOCS_PATH,
        model=config.OLLAMA_EMBED_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        timeout=config.OLLAMA_TIMEOUT,
        top_k=args.top_k,
    )

    print(f"Query: {args.query}")
    if results and results[0]["expanded_query"] != args.query:
        print(f"Expanded query: {results[0]['expanded_query']}")
    print()

    for rank, result in enumerate(results, start=1):
        doc = result["document"]
        preview = str(result["text"]).replace("\n", " ")
        if len(preview) > 500:
            preview = preview[:500].rstrip() + "..."
        print(f"[{rank}] score={result['score']:.4f}")
        print(f"    source={result['source']}")
        print(f"    title={doc.get('title')}")
        print(f"    wiki_type={doc.get('wiki_type')}")
        print(f"    chunk_id={result['chunk_id']}")
        print(f"    {preview}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
