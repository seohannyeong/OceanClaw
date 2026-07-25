#!/usr/bin/env python3
"""Search sensor event FAISS index."""

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


def print_results(query: str, results: list[dict]) -> None:
    print(f"Query: {query}")
    if results and results[0].get("expanded_query") != query:
        print(f"Expanded query: {results[0]['expanded_query']}")
    print()

    for rank, result in enumerate(results, start=1):
        doc = result["document"]
        preview = str(result["text"]).replace("\n", " ")
        if len(preview) > 350:
            preview = preview[:350].rstrip() + "..."
        print(f"[{rank}] score={result['score']:.4f}")
        print(
            f"    event_id={doc.get('event_id')} "
            f"component={doc.get('component')} severity={doc.get('severity')} "
            f"running_hours={doc.get('running_hours')}"
        )
        print(f"    {preview}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Search sensor event FAISS index.")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--faiss", type=Path, default=config.SENSOR_FAISS_PATH)
    parser.add_argument("--docs", type=Path, default=config.SENSOR_DOCS_PATH)
    parser.add_argument("--model", default=config.OLLAMA_EMBED_MODEL)
    parser.add_argument("--ollama-url", default=config.OLLAMA_BASE_URL)
    parser.add_argument("--timeout", type=int, default=config.OLLAMA_TIMEOUT)
    args = parser.parse_args()

    check_ollama(args.ollama_url, args.timeout)

    if args.query:
        results = search_faiss_index(
            query=args.query,
            faiss_path=config.project_path(str(args.faiss)),
            docs_path=config.project_path(str(args.docs)),
            model=args.model,
            base_url=args.ollama_url,
            timeout=args.timeout,
            top_k=args.top_k,
        )
        print_results(args.query, results)
        return 0

    print("Sensor event retriever is ready. Type a query, or type 'exit' to quit.")
    while True:
        query = input("\nQuery> ").strip()
        if query.lower() in {"exit", "quit", "q"}:
            break
        if not query:
            continue
        results = search_faiss_index(
            query=query,
            faiss_path=config.project_path(str(args.faiss)),
            docs_path=config.project_path(str(args.docs)),
            model=args.model,
            base_url=args.ollama_url,
            timeout=args.timeout,
            top_k=args.top_k,
        )
        print_results(query, results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
