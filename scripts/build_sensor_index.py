#!/usr/bin/env python3
"""Build FAISS index from sensor event CSV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config
from oceanclaw.ollama_embed import check_ollama
from oceanclaw.vectorstore import build_docs_faiss_index, load_csv_docs


def main() -> int:
    parser = argparse.ArgumentParser(description="Build sensor event FAISS index.")
    parser.add_argument("--events", type=Path, default=config.SENSOR_EVENTS_PATH)
    parser.add_argument("--faiss", type=Path, default=config.SENSOR_FAISS_PATH)
    parser.add_argument("--docs", type=Path, default=config.SENSOR_DOCS_PATH)
    parser.add_argument("--model", default=config.OLLAMA_EMBED_MODEL)
    parser.add_argument("--ollama-url", default=config.OLLAMA_BASE_URL)
    parser.add_argument("--timeout", type=int, default=config.OLLAMA_TIMEOUT)
    args = parser.parse_args()

    events_path = config.project_path(str(args.events))
    faiss_path = config.project_path(str(args.faiss))
    docs_path = config.project_path(str(args.docs))

    check_ollama(args.ollama_url, args.timeout)
    documents = load_csv_docs(events_path, id_field="event_id")
    count = build_docs_faiss_index(
        documents=documents,
        source_path=events_path,
        faiss_path=faiss_path,
        docs_path=docs_path,
        model=args.model,
        base_url=args.ollama_url,
        timeout=args.timeout,
        text_field="text",
    )

    print(f"[OK] indexed {count} sensor events")
    print(f"FAISS: {faiss_path}")
    print(f"Docs: {docs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
