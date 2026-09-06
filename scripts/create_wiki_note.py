#!/usr/bin/env python3
"""Create a reusable Obsidian Wiki note from OceanClaw retrieval."""

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
    parser = argparse.ArgumentParser(
        description="Create a reusable Obsidian Wiki note from OceanClaw retrieval."
    )
    parser.add_argument("topic", help="Wiki note topic, for example: 엔진 오일 점검")
    parser.add_argument(
        "--route",
        choices=["manual", "sensor", "wiki", "both", "all"],
        default="all",
        help="Evidence sources to search before writing the note.",
    )
    parser.add_argument(
        "--type",
        choices=["component", "procedure", "log"],
        dest="wiki_type",
        help="Wiki note type. If omitted, OceanClaw infers it from the topic.",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=config.WIKI_DIR / "procedures",
        help="Directory where the Markdown note will be saved.",
    )
    parser.add_argument("--filename", help="Optional Markdown filename.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Rebuild the Wiki FAISS index after saving the note.",
    )
    args = parser.parse_args()

    check_ollama(config.OLLAMA_BASE_URL, config.OLLAMA_TIMEOUT)
    result = generate_wiki_document(
        topic=args.topic,
        route=args.route,
        wiki_type=args.wiki_type,
        top_k=args.top_k,
        min_score=args.min_score,
        output_dir=args.output_dir,
        filename=args.filename,
        overwrite=args.overwrite,
        auto_rename=True,
        rebuild_index=args.rebuild_index,
    )

    print("[OK] Wiki note saved")
    print(f"Topic: {result['topic']}")
    print(f"Type: {result['wiki_type']}")
    print(f"Route: {result['route']}")
    print(f"Saved to: {result['path']}")
    print()
    print("Sources:")
    for source in result["sources"]:
        print(f"- {source}")

    if result.get("index"):
        index = result["index"]
        print()
        print(f"[OK] rebuilt wiki index: {index['chunk_count']} chunks, {index['indexed_count']} indexed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
