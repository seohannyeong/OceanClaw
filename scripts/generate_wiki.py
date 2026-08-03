#!/usr/bin/env python3
"""Generate an Obsidian-compatible Wiki document from RAG evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config
from oceanclaw.ollama_embed import check_ollama
from oceanclaw.wiki_writer import generate_wiki_document

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an OceanClaw Wiki document.")
    parser.add_argument("topic", help="Wiki topic to generate")
    parser.add_argument("--route", choices=["manual", "sensor", "both"], default="both")
    parser.add_argument("--type", choices=["component", "procedure", "log"], dest="wiki_type")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    check_ollama(config.OLLAMA_BASE_URL, config.OLLAMA_TIMEOUT)
    result = generate_wiki_document(
        topic=args.topic,
        route=args.route,
        wiki_type=args.wiki_type,
        top_k=args.top_k,
        output_path=args.out,
        overwrite=args.overwrite,
    )

    print("[OK] Wiki document generated")
    print(f"Topic: {result['topic']}")
    print(f"Type: {result['wiki_type']}")
    print(f"Saved to: {result['path']}")
    print("Sources:")
    for source in result["sources"]:
        print(f"- {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
