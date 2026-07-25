#!/usr/bin/env python3
"""Extract PDF pages to JSONL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config
from oceanclaw.pdf_extract import extract_pdf_to_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract PDF text page by page.")
    parser.add_argument("--pdf", type=Path, default=config.PDF_PATH)
    parser.add_argument("--out", type=Path, default=config.PDF_PAGES_PATH)
    args = parser.parse_args()

    pdf_path = config.project_path(str(args.pdf))
    output_path = config.project_path(str(args.out))

    count = extract_pdf_to_jsonl(pdf_path, output_path)
    print(f"[OK] extracted {count} pages")
    print(f"PDF: {pdf_path}")
    print(f"Saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
