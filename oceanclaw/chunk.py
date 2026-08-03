"""Create retrieval chunks from extracted PDF pages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from langchain_text_splitters import RecursiveCharacterTextSplitter


DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def chunk_text(text: str, size: int, overlap: int) -> List[str]:
    if size <= 0:
        raise ValueError("chunk size must be greater than 0")
    if overlap < 0:
        raise ValueError("chunk overlap must be greater than or equal to 0")
    if overlap >= size:
        raise ValueError("chunk overlap must be smaller than chunk size")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=DEFAULT_SEPARATORS,
        length_function=len,
    )
    return [chunk.strip() for chunk in splitter.split_text(normalized) if chunk.strip()]


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
