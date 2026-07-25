"""Extract page text from PDF files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable

from pypdf import PdfReader


def iter_pdf_pages(pdf_path: Path) -> Iterable[Dict[str, object]]:
    reader = PdfReader(str(pdf_path))
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        yield {
            "source": pdf_path.name,
            "page": page_num,
            "text": text,
        }


def extract_pdf_to_jsonl(pdf_path: Path, output_path: Path) -> int:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for record in iter_pdf_pages(pdf_path):
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count
