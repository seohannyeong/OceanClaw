"""Create retrieval chunks from extracted PDF pages."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List


def split_paragraphs(text: str) -> List[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    blocks = [block.strip() for block in re.split(r"\n\s*\n+", text) if block.strip()]
    if len(blocks) > 1:
        return blocks

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return lines if lines else [text]


def split_long_text(text: str, size: int) -> List[str]:
    words = text.split()
    if not words:
        return []

    parts: List[str] = []
    current = ""
    for word in words:
        next_text = f"{current} {word}".strip()
        if current and len(next_text) > size:
            parts.append(current)
            current = word
        else:
            current = next_text
    if current:
        parts.append(current)
    return parts


def chunk_text(text: str, size: int, overlap: int) -> List[str]:
    if size <= 0:
        raise ValueError("chunk size must be greater than 0")
    if overlap < 0:
        raise ValueError("chunk overlap must be greater than or equal to 0")
    if overlap >= size:
        raise ValueError("chunk overlap must be smaller than chunk size")

    chunks: List[str] = []
    current = ""

    for paragraph in split_paragraphs(text):
        candidates = [paragraph]
        if len(paragraph) > size:
            candidates = split_long_text(paragraph, size)

        for candidate in candidates:
            next_text = f"{current}\n{candidate}".strip() if current else candidate
            if current and len(next_text) > size:
                chunks.append(current)
                tail = current[-overlap:] if overlap else ""
                current = f"{tail}\n{candidate}".strip() if tail else candidate
            else:
                current = next_text

    if current:
        chunks.append(current)
    return chunks


def read_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def chunk_pdf_pages(
    pages_path: Path,
    output_path: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> int:
    if not pages_path.exists():
        raise FileNotFoundError(f"PDF pages JSONL not found: {pages_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for page_record in read_jsonl(pages_path):
            source = str(page_record["source"])
            page = int(page_record["page"])
            text = str(page_record.get("text", ""))
            source_stem = Path(source).stem

            for chunk_index, chunk in enumerate(
                chunk_text(text, chunk_size, chunk_overlap)
            ):
                record = {
                    "source": source,
                    "page": page,
                    "chunk_id": f"{source_stem}-p{page}-c{chunk_index}",
                    "text": chunk,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1

    return count
