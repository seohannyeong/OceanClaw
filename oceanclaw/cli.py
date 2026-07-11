"""터미널 질의응답 인터페이스."""

from __future__ import annotations

from typing import Dict, List, Tuple

from .pipeline import answer


def _print_sources(pdf_hits: List[Tuple[Dict, float]], csv_hits: List[Tuple[Dict, float]]) -> None:
    print("\n  📎 근거 출처")
    for doc, score in pdf_hits:
        preview = doc["text"][:70].replace("\n", " ")
        print(f"   • 매뉴얼 p.{doc['page']} (유사도 {score:.2f}) — {preview}...")
    for doc, score in csv_hits:
        preview = doc["text"][:70].replace("\n", " ")
        print(f"   • 정비이력 #{doc['row']} (유사도 {score:.2f}) — {preview}...")


def ask_once(query: str) -> None:
    answer_text, pdf_hits, csv_hits = answer(query)
    print("\n🤖 OceanClaw")
    print(answer_text)
    _print_sources(pdf_hits, csv_hits)


def run_repl() -> None:
    print("=" * 60)
    print("  ⚓ OceanClaw - 선박 정비 AI Agent (MVP)")
    print("  질문을 입력하세요. 종료: exit / quit / 빈 줄+Ctrl-C")
    print("=" * 60)
    while True:
        try:
            query = input("\n기관사> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n안전 항해 되세요. ⚓")
            break
        if not query:
            continue
        if query.lower() in {"exit", "quit", "종료"}:
            print("안전 항해 되세요. ⚓")
            break
        try:
            ask_once(query)
        except Exception as exc:  # 현장에서 죽지 않게
            print(f"\n⚠️  오류: {exc}")
