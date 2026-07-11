"""PDF 매뉴얼과 CSV 정비 이력을 검색 가능한 문서(dict) 리스트로 변환한다.

문서 dict 형식:
  {
    "id": "pdf-3-1",         # 고유 id
    "kind": "pdf" | "csv",
    "source": "manual.pdf",  # 파일명
    "page": 142,             # pdf만 (1부터)
    "row": 5,                # csv만 (1부터)
    "text": "...",           # 임베딩/검색 대상 텍스트
    "raw": {...},            # csv 원본 행 (csv만)
  }
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from . import config


def _split_text(text: str, size: int, overlap: int) -> List[str]:
    """문단 단위로 묶되 size를 넘지 않게 청크로 자른다."""
    text = text.strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 1 > size:
            chunks.append(current)
            # overlap: 직전 청크 꼬리를 다음 청크 앞에 살짝 포함
            tail = current[-overlap:] if overlap else ""
            current = (tail + " " + para).strip()
        else:
            current = (current + " " + para).strip() if current else para
    if current:
        chunks.append(current)
    return chunks


def load_pdf_chunks(path: Path) -> List[Dict]:
    """PDF를 페이지별로 읽고 청크로 나눠 페이지 번호를 보존한다."""
    from pypdf import PdfReader

    if not path.exists():
        raise FileNotFoundError(
            f"PDF를 찾을 수 없습니다: {path}\n"
            "샘플을 만들려면: python scripts/make_sample_data.py"
        )

    reader = PdfReader(str(path))
    docs: List[Dict] = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for idx, chunk in enumerate(_split_text(text, config.CHUNK_SIZE, config.CHUNK_OVERLAP)):
            docs.append(
                {
                    "id": f"pdf-{page_no}-{idx}",
                    "kind": "pdf",
                    "source": path.name,
                    "page": page_no,
                    "text": chunk,
                }
            )
    return docs


def load_csv_docs(path: Path) -> List[Dict]:
    """CSV의 각 행을 하나의 검색 문서로 만든다."""
    if not path.exists():
        raise FileNotFoundError(
            f"CSV를 찾을 수 없습니다: {path}\n"
            "샘플을 만들려면: python scripts/make_sample_data.py"
        )

    docs: List[Dict] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            text = "; ".join(f"{k}: {v}" for k, v in row.items() if v)
            docs.append(
                {
                    "id": f"csv-{i}",
                    "kind": "csv",
                    "source": path.name,
                    "row": i,
                    "text": text,
                    "raw": row,
                }
            )
    return docs
