#!/usr/bin/env python3
"""Search the AIS voyage-event FAISS index."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config
from oceanclaw.ais_search import search_ais_hybrid
from oceanclaw.ollama_embed import check_ollama


def print_results(query: str, results: list[dict]) -> None:
    print(f"Query: {query}\n")
    for rank, result in enumerate(results, start=1):
        doc = result["document"]
        print(f"[{rank}] score={result['score']:.4f}")
        print(
            f"    vessel={doc.get('vessel_name') or '-'} mmsi={doc.get('mmsi')} "
            f"event={doc.get('event_type')}"
        )
        print(f"    period={doc.get('start_time')} ~ {doc.get('end_time')}")
        print(f"    {str(result['text'])[:350]}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Search AIS voyage events.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--faiss", type=Path, default=config.AIS_FAISS_PATH)
    parser.add_argument("--docs", type=Path, default=config.AIS_DOCS_PATH)
    parser.add_argument("--model", default=config.OLLAMA_EMBED_MODEL)
    parser.add_argument("--ollama-url", default=config.OLLAMA_BASE_URL)
    parser.add_argument("--timeout", type=int, default=config.OLLAMA_TIMEOUT)
    args = parser.parse_args()
    check_ollama(args.ollama_url, args.timeout)
    results = search_ais_hybrid(
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


if __name__ == "__main__":
    raise SystemExit(main())
