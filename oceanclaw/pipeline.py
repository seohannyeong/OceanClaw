"""전체 파이프라인: 인덱스 빌드 + 질문 답변."""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from . import config, gemini
from .ingest import load_csv_docs, load_pdf_chunks #데이터 읽어오는 함수 
from .vectorstore import VectorStore


def build_index() -> Dict[str, int]:
    """PDF/CSV를 임베딩해 FAISS 인덱스를 만들고 저장한다."""
    os.makedirs(config.INDEX_DIR, exist_ok=True)

    pdf_docs = load_pdf_chunks(config.PDF_PATH)
    csv_docs = load_csv_docs(config.CSV_PATH)

    print(f"  PDF 청크 {len(pdf_docs)}개, CSV 행 {len(csv_docs)}개 임베딩 중...")
    pdf_vecs = gemini.embed_texts([d["text"] for d in pdf_docs])
    csv_vecs = gemini.embed_texts([d["text"] for d in csv_docs])

    VectorStore.build(pdf_docs, pdf_vecs).save(config.PDF_INDEX_PREFIX)
    VectorStore.build(csv_docs, csv_vecs).save(config.CSV_INDEX_PREFIX)

    return {"pdf_chunks": len(pdf_docs), "csv_rows": len(csv_docs)}


def _format_context(
    pdf_hits: List[Tuple[Dict, float]], csv_hits: List[Tuple[Dict, float]]
) -> str:
    lines: List[str] = []
    if pdf_hits:
        lines.append("### 기술 매뉴얼 검색 결과")
        for doc, score in pdf_hits:
            lines.append(f"[매뉴얼 p.{doc['page']}] {doc['text']}")
    if csv_hits:
        lines.append("\n### 정비 이력 검색 결과")
        for doc, score in csv_hits:
            lines.append(f"[정비이력 #{doc['row']}] {doc['text']}")
    return "\n".join(lines) if lines else "(검색 결과 없음)"


def answer(query: str):
    """질문 → 검색 → Gemini 답변. (answer_text, pdf_hits, csv_hits) 반환."""
    pdf_store = VectorStore.load(config.PDF_INDEX_PREFIX)
    csv_store = VectorStore.load(config.CSV_INDEX_PREFIX)

    qvec = gemini.embed_query(query)
    pdf_hits = pdf_store.search(qvec, config.TOP_K_PDF)
    csv_hits = csv_store.search(qvec, config.TOP_K_CSV)

    context = _format_context(pdf_hits, csv_hits)
    answer_text = gemini.generate_answer(query, context)
    return answer_text, pdf_hits, csv_hits
