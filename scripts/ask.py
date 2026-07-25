#!/usr/bin/env python3
"""Ask a question and generate a grounded Korean answer."""

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
    if result["expanded_query"] != result["question"]:
        print(f"Expanded query: {result['expanded_query']}")
    print()
    print(result["answer"])
    print()

    print("출처:")
    for source in result["sources"]:
        print(f"- {source}")
    print()

    print("검색 근거:")
    for rank, item in enumerate(result["results"], start=1):
        preview = str(item["text"]).replace("\n", " ")
        if len(preview) > 300:
            preview = preview[:300].rstrip() + "..."
        print(
            f"[{rank}] score={item['score']:.4f} "
            f"page={item['page']} chunk_id={item['chunk_id']}"
        )
        if show_context:
            print(f"    {preview}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask OceanClaw a question.")
    parser.add_argument("question", nargs="?", help="Question to ask")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--show-context", action="store_true")
    args = parser.parse_args()

    check_ollama(config.OLLAMA_BASE_URL, config.OLLAMA_TIMEOUT)

    if args.question:
        result = answer_question(
            question=args.question,
            top_k=args.top_k,
            min_score=args.min_score,
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
        )
        print_answer(result, args.show_context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
