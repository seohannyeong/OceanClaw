#!/usr/bin/env python3
"""Ask OceanClaw using manual, sensor, and wiki retrieval."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config
from oceanclaw.answer import answer_question
from oceanclaw.ollama_embed import check_ollama

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def print_answer(result: dict, show_context: bool) -> None:
    print(f"Question: {result['question']}")
    print(f"Route: {result['route']}")
    if result["expanded_query"] != result["question"]:
        print(f"Expanded query: {result['expanded_query']}")
    print()
    print(result["answer"])
    print()

    print("출처:")
    for source in result["sources"]:
        print(f"- {source}")
    print()

    if result.get("wiki_log_path"):
        print(f"Wiki log saved: {result['wiki_log_path']}")
        print()

    print("검색 근거:")
    for rank, item in enumerate(result["results"], start=1):
        preview = str(item["text"]).replace("\n", " ")
        if len(preview) > 300:
            preview = preview[:300].rstrip() + "..."

        if item.get("kind") == "sensor":
            doc = item["document"]
            print(
                f"[{rank}] sensor score={item['score']:.4f} "
                f"event_id={doc.get('event_id')} "
                f"component={doc.get('component')} "
                f"severity={doc.get('severity')}"
            )
        elif item.get("kind") == "wiki":
            doc = item["document"]
            print(
                f"[{rank}] wiki score={item['score']:.4f} "
                f"source={item.get('source')} "
                f"title={doc.get('title')} "
                f"wiki_type={doc.get('wiki_type')}"
            )
        else:
            print(
                f"[{rank}] manual score={item['score']:.4f} "
                f"page={item['page']} chunk_id={item['chunk_id']}"
            )

        if show_context:
            print(f"    {preview}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask OceanClaw a question.")
    parser.add_argument("question", nargs="?", help="Question to ask")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--save-log", action="store_true", help="Save answer to wiki/logs")
    parser.add_argument(
        "--route",
        choices=["manual", "sensor", "wiki", "both", "all"],
        help="Override automatic routing",
    )
    parser.add_argument("--show-context", action="store_true")
    args = parser.parse_args()

    check_ollama(config.OLLAMA_BASE_URL, config.OLLAMA_TIMEOUT)

    if args.question:
        result = answer_question(
            question=args.question,
            top_k=args.top_k,
            min_score=args.min_score,
            route_override=args.route,
            save_log=args.save_log,
        )
        print_answer(result, args.show_context)
        return 0

    print("OceanClaw ask is ready. Type a question, or type 'exit' to quit.")
    while True:
        question = input("\nQuestion> ").strip()
        if question.lower() in {"exit", "quit", "q"}:
            break
        if not question:
            continue
        result = answer_question(
            question=question,
            top_k=args.top_k,
            min_score=args.min_score,
            route_override=args.route,
            save_log=args.save_log,
        )
        print_answer(result, args.show_context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
