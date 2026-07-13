"""전체 파이프라인: 인덱스 빌드 + 질문 답변."""

from __future__ import annotations

import os
from typing import Dict, List, Literal, Tuple

from . import config, llm
from .ingest import load_csv_docs, load_pdf_chunks #데이터 읽어오는 함수 
from .vectorstore import VectorStore


SearchRoute = Literal["manual", "logs", "both"]

MANUAL_KEYWORDS = {
    "토크",
    "조임",
    "간격",
    "clearance",
    "권장",
    "주기",
    "스펙",
    "사양",
    "매뉴얼",
    "절차",
    "허용",
    "한계",
    "nm",
    "mm",
    "bar",
}

LOG_KEYWORDS = {
    "언제",
    "마지막",
    "최근",
    "이력",
    "기록",
    "작업자",
    "수행",
    "상태",
    "추세",
    "지난",
    "개월",
    "날짜",
    "running",
    "hours",
    "#",
    "번",
}

QUERY_EXPANSIONS = {
    "메인 베어링": "main bearing main bearings",
    "베어링": "bearing",
    "볼트": "bolt stud",
    "토크": "torque tightening torque",
    "조임": "tightening",
    "간격": "clearance oil clearance gap",
    "권장": "recommended",
    "주기": "maintenance interval inspection interval",
    "실린더": "cylinder",
    "피스톤 링": "piston rings",
    "피스톤링": "piston rings",
    "교체": "replacement renewal replace",
    "점검": "inspection",
    "정비": "maintenance",
    "마지막": "last date maintenance log",
    "최근": "recent latest maintenance log",
}


def _count_keywords(query: str, keywords: set[str]) -> int:
    lowered = query.lower()
    return sum(1 for keyword in keywords if keyword in lowered)


def _route_query(query: str) -> SearchRoute:
    manual_score = _count_keywords(query, MANUAL_KEYWORDS)
    log_score = _count_keywords(query, LOG_KEYWORDS)

    if manual_score and log_score:
        return "both"
    if log_score:
        return "logs"
    if manual_score:
        return "manual"
    return "both"


def _expand_query(query: str) -> str:
    lowered = query.lower()
    expansions = [value for key, value in QUERY_EXPANSIONS.items() if key in lowered]
    if not expansions:
        return query
    return f"{query}\n{' '.join(expansions)}"


def _rerank_csv_hits(query: str, hits: List[Tuple[Dict, float]]) -> List[Tuple[Dict, float]]:
    lowered = query.lower()
    reranked: List[Tuple[Dict, float]] = []
    wants_recent = any(token in lowered for token in {"최근", "마지막", "latest", "last"})

    for doc, score in hits:
        text = doc["text"].lower()
        adjusted = score
        raw = doc.get("raw", {})
        date = raw.get("date", "")

        if "#3" in lowered and "#3" in text:
            adjusted += 0.18
        if "메인 베어링" in lowered and "main bearing" in text:
            adjusted += 0.12
        if "4번" in lowered and "cylinder 4" in text:
            adjusted += 0.20
        if "피스톤" in lowered and "piston ring" in text:
            adjusted += 0.15
        if "교체" in lowered and "replacement" in text:
            adjusted += 0.15
        if "점검" in lowered and "inspection" in text:
            adjusted += 0.08
        if wants_recent and date:
            adjusted += min(int(date[:4]) - 2024, 3) * 0.04

        reranked.append((doc, adjusted))

    return sorted(reranked, key=lambda item: item[1], reverse=True)


def _rerank_pdf_hits(query: str, hits: List[Tuple[Dict, float]]) -> List[Tuple[Dict, float]]:
    lowered = query.lower()
    reranked: List[Tuple[Dict, float]] = []
    wants_interval = any(token in lowered for token in {"권장", "주기", "교체 간격", "interval"})
    wants_clearance = "간격" in lowered and "교체 간격" not in lowered

    for doc, score in hits:
        text = doc["text"].lower()
        adjusted = score

        if "토크" in lowered and "tightening torque" in text:
            adjusted += 0.18
        if wants_interval and "recommended maintenance intervals" in text:
            adjusted += 0.18
        if wants_clearance and "clearance" in text:
            adjusted += 0.18
        if "피스톤" in lowered and "piston ring" in text:
            adjusted += 0.12
        if "실린더" in lowered and "cylinder" in text:
            adjusted += 0.10
        if "메인 베어링" in lowered and "main bearing" in text:
            adjusted += 0.10

        reranked.append((doc, adjusted))

    return sorted(reranked, key=lambda item: item[1], reverse=True)


def build_index() -> Dict[str, int]:
    """PDF/CSV를 임베딩해 FAISS 인덱스를 만들고 저장한다."""
    os.makedirs(config.INDEX_DIR, exist_ok=True)

    pdf_docs = load_pdf_chunks(config.PDF_PATH)
    csv_docs = load_csv_docs(config.CSV_PATH)

    print(f"  PDF 청크 {len(pdf_docs)}개, CSV 행 {len(csv_docs)}개 임베딩 중...")
    pdf_vecs = llm.embed_texts([d["text"] for d in pdf_docs])
    csv_vecs = llm.embed_texts([d["text"] for d in csv_docs])

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

    route = _route_query(query)
    qvec = llm.embed_query(_expand_query(query))
    pdf_hits = pdf_store.search(qvec, config.TOP_K_PDF) if route in {"manual", "both"} else []
    pdf_hits = _rerank_pdf_hits(query, pdf_hits)
    csv_hits = csv_store.search(qvec, config.TOP_K_CSV) if route in {"logs", "both"} else []
    csv_hits = _rerank_csv_hits(query, csv_hits)

    context = _format_context(pdf_hits, csv_hits)
    answer_text = llm.generate_answer(query, context)
    return answer_text, pdf_hits, csv_hits
