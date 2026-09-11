#!/usr/bin/env python3
"""Search PDF chunks with Ollama embeddings and FAISS."""

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
from oceanclaw.contextual_manual import search_contextual_manual

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def print_results(query: str, results: list[dict]) -> None:
    print(f"Query: {query}")
    if results and results[0].get("expanded_query") != query:
        print(f"Expanded query: {results[0]['expanded_query']}")
    print()
    for rank, result in enumerate(results, start=1):
        preview = str(result["text"]).replace("\n", " ")
        if len(preview) > 450:
            preview = preview[:450].rstrip() + "..."
        print(f"[{rank}] score={result['score']:.4f}")
        print(f"    page={result['page']} chunk_id={result['chunk_id']}")
        print(f"    {preview}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Search PDF FAISS index.")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--profile", choices=["titles", "legacy"], default="titles")
    parser.add_argument("--index-dir", default=config.TITLED_MANUAL_INDEX_DIR)
    parser.add_argument("--faiss", type=Path, default=config.PDF_FAISS_PATH)
    parser.add_argument("--docs", type=Path, default=config.PDF_DOCS_PATH)
    parser.add_argument("--model", default=config.OLLAMA_EMBED_MODEL)
    parser.add_argument("--ollama-url", default=config.OLLAMA_BASE_URL)
    parser.add_argument("--timeout", type=int, default=config.OLLAMA_TIMEOUT)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")

    check_ollama(args.ollama_url, args.timeout)

    def search(query):
        if args.profile == "titles":
            return search_contextual_manual(query, args.top_k, directory=args.index_dir,
                                             base_url=args.ollama_url, timeout=args.timeout)
        return search_faiss_index(query, config.project_path(str(args.faiss)),
                                  config.project_path(str(args.docs)), args.model,
                                  args.ollama_url, args.timeout, args.top_k)

    if args.query:
        results = search(args.query)
        print_results(args.query, results)
        return 0

    print("FAISS dense retriever is ready. Type a query, or type 'exit' to quit.")
    while True:
        query = input("\nQuery> ").strip()
        if query.lower() in {"exit", "quit", "q"}:
            break
        if not query:
            continue
        results = search(query)
        print_results(query, results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
