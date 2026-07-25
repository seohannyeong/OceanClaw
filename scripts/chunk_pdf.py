#!/usr/bin/env python3
"""Create PDF chunks from extracted page JSONL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config
from oceanclaw.chunk import chunk_pdf_pages


def main() -> int:
    parser = argparse.ArgumentParser(description="Chunk extracted PDF pages.")
    parser.add_argument("--pages", type=Path, default=config.PDF_PAGES_PATH)
    parser.add_argument("--out", type=Path, default=config.PDF_CHUNKS_PATH)
    parser.add_argument("--size", type=int, default=config.CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=config.CHUNK_OVERLAP)
    args = parser.parse_args()

    pages_path = config.project_path(str(args.pages))
    output_path = config.project_path(str(args.out))

    count = chunk_pdf_pages(
        pages_path=pages_path,
        output_path=output_path,
        chunk_size=args.size,
        chunk_overlap=args.overlap,
    )

    print(f"[OK] created {count} chunks")
    print(f"Pages: {pages_path}")
    print(f"Saved to: {output_path}")
    print(f"CHUNK_SIZE: {args.size}")
    print(f"CHUNK_OVERLAP: {args.overlap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
