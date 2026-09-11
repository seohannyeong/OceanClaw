#!/usr/bin/env python3
"""Build FAISS index from PDF chunks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config
from oceanclaw.ollama_embed import check_ollama
from oceanclaw.vectorstore import build_faiss_index
from oceanclaw.vectorstore import build_docs_faiss_index, load_jsonl
from oceanclaw.manual_titles import annotate, bookmarks
from pypdf import PdfReader


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PDF FAISS index.")
    parser.add_argument("--chunks", type=Path, default=config.PDF_CHUNKS_PATH)
    parser.add_argument("--faiss", type=Path, default=config.PDF_FAISS_PATH)
    parser.add_argument("--docs", type=Path, default=config.PDF_DOCS_PATH)
    parser.add_argument("--model", default=config.OLLAMA_EMBED_MODEL)
    parser.add_argument("--ollama-url", default=config.OLLAMA_BASE_URL)
    parser.add_argument("--timeout", type=int, default=config.OLLAMA_TIMEOUT)
    parser.add_argument("--legacy", action="store_true", help="Build the old body-only nomic index")
    parser.add_argument("--pdf", type=Path, default=config.PDF_PATH)
    parser.add_argument("--pages", type=Path, default=config.PDF_PAGES_PATH)
    parser.add_argument("--index-dir", default=config.TITLED_MANUAL_INDEX_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    chunks_path = config.project_path(str(args.chunks))
    faiss_path = config.project_path(str(args.faiss))
    docs_path = config.project_path(str(args.docs))

    check_ollama(args.ollama_url, args.timeout)
    if not args.legacy:
        directory = config.project_path(args.index_dir)
        if directory.exists() and any(directory.iterdir()) and not args.overwrite:
            parser.error("Titled index already exists. Use it as-is, or pass --overwrite after changing the documents.")
        docs, missing = annotate(load_jsonl(config.project_path(str(args.pages))),
                                 load_jsonl(chunks_path), bookmarks(PdfReader(config.project_path(str(args.pdf)))))
        count = build_docs_faiss_index(docs, chunks_path, directory / "pdf.faiss", directory / "pdf_docs.json",
                                       "bge-m3", args.ollama_url, args.timeout, text_field="embedding_text")
        (directory / "heading_audit.json").write_text(json.dumps({"unmatched_bookmarks": missing,
            "chunks_without_title": [d["chunk_id"] for d in docs if not d["sections"]]}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] indexed {count} titled chunks with bge-m3: {directory}")
        return 0
    count = build_faiss_index(
        chunks_path=chunks_path,
        faiss_path=faiss_path,
        docs_path=docs_path,
        model=args.model,
        base_url=args.ollama_url,
        timeout=args.timeout,
    )

    print(f"[OK] indexed {count} chunks")
    print(f"FAISS: {faiss_path}")
    print(f"Docs: {docs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
