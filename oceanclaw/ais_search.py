"""Hybrid AIS retrieval using structured filters and FAISS similarity."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .ollama_embed import embed_text


@dataclass(frozen=True)
class AISQueryFilters:
    event_types: tuple[str, ...] = ()
    min_duration_minutes: float | None = None
    max_duration_minutes: float | None = None
    mmsi: str | None = None
    date_prefix: str | None = None
    sort_by_duration: bool = False

    @property
    def active(self) -> bool:
        return bool(
            self.event_types
            or self.min_duration_minutes is not None
            or self.max_duration_minutes is not None
            or self.mmsi
            or self.date_prefix
        )


STATUS_RULES = (
    (
        ("정박", "투묘", "닻", "anchor", "anchored", "계류", "접안", "moored", "berth"),
        ("anchored", "moored"),
        "anchored at anchor moored berthed vessel",
    ),
    (("좌초", "aground", "grounded"), ("aground",), "aground grounded vessel"),
    (("조업", "어업", "fishing"), ("fishing",), "fishing vessel engaged in fishing"),
    (("저속", "low speed", "low-speed"), ("low-speed movement",), "low-speed vessel movement"),
    (("정지", "멈춘", "stationary", "stopped"), ("stationary",), "stationary stopped vessel"),
    (("범선", "sailing"), ("sailing",), "vessel under way sailing"),
    (("운항 중", "항해 중", "이동 중", "underway", "under way"), ("underway",), "vessel under way using engine"),
)

LONG_DURATION_TERMS = ("장시간", "오랫동안", "오래", "최장", "longest", "long duration")


def _contains_term(query: str, term: str) -> bool:
    if re.fullmatch(r"[a-z -]+", term):
        return re.search(rf"\b{re.escape(term)}\b", query) is not None
    return term in query


def _duration_filter(query: str) -> tuple[float | None, float | None]:
    pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*(시간|hours?|hrs?|분|minutes?|mins?)"
        r"\s*(이상|초과|이하|미만|at least|more than|over|under|less than)?",
        re.IGNORECASE,
    )
    match = pattern.search(query)
    if not match:
        return None, None

    value = float(match.group(1))
    unit = match.group(2).lower()
    minutes = value * 60 if unit in {"시간", "hour", "hours", "hr", "hrs"} else value
    comparator = (match.group(3) or "").lower()
    if comparator in {"이하", "미만", "under", "less than"}:
        return None, minutes
    if comparator in {"이상", "초과", "at least", "more than", "over"}:
        return minutes, None
    return None, None


def parse_ais_query(query: str) -> tuple[AISQueryFilters, str]:
    normalized = " ".join(query.lower().split())
    event_types: tuple[str, ...] = ()
    expansion = ""
    for terms, mapped_types, English_expansion in STATUS_RULES:
        if any(_contains_term(normalized, term) for term in terms):
            event_types = mapped_types
            expansion = English_expansion
            break

    minimum, maximum = _duration_filter(normalized)
    mmsi_match = re.search(r"(?<!\d)(\d{9})(?!\d)", normalized)
    date_match = re.search(r"\b(20\d{2})[-./](\d{1,2})(?:[-./](\d{1,2}))?\b", normalized)
    if not date_match:
        date_match = re.search(r"\b(20\d{2})년\s*(\d{1,2})월(?:\s*(\d{1,2})일)?", normalized)
    date_prefix = None
    if date_match:
        year, month, day = date_match.groups()
        date_prefix = f"{year}-{int(month):02d}"
        if day:
            date_prefix += f"-{int(day):02d}"

    sort_by_duration = any(term in normalized for term in LONG_DURATION_TERMS)
    filters = AISQueryFilters(
        event_types=event_types,
        min_duration_minutes=minimum,
        max_duration_minutes=maximum,
        mmsi=mmsi_match.group(1) if mmsi_match else None,
        date_prefix=date_prefix,
        sort_by_duration=sort_by_duration,
    )
    expanded_query = f"{query} {expansion}".strip() if expansion else query
    return filters, expanded_query


@lru_cache(maxsize=2)
def _load_resources(faiss_path_text: str, docs_path_text: str):
    import faiss
    import numpy as np

    faiss_path = Path(faiss_path_text)
    docs_path = Path(docs_path_text)
    if not faiss_path.exists():
        raise FileNotFoundError(f"FAISS index not found: {faiss_path}")
    if not docs_path.exists():
        raise FileNotFoundError(f"Docs metadata not found: {docs_path}")
    index = faiss.deserialize_index(np.frombuffer(faiss_path.read_bytes(), dtype="uint8"))
    metadata = json.loads(docs_path.read_text(encoding="utf-8"))
    documents = metadata["documents"]
    if index.ntotal != len(documents):
        raise ValueError("AIS index and metadata document counts do not match")
    return index, documents


def _as_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _matches(doc: dict, filters: AISQueryFilters) -> bool:
    if filters.event_types and doc.get("event_type") not in filters.event_types:
        return False
    duration = _as_float(doc.get("duration_minutes"))
    if filters.min_duration_minutes is not None and duration < filters.min_duration_minutes:
        return False
    if filters.max_duration_minutes is not None and duration > filters.max_duration_minutes:
        return False
    if filters.mmsi and str(doc.get("mmsi", "")) != filters.mmsi:
        return False
    if filters.date_prefix and not str(doc.get("start_time", "")).startswith(filters.date_prefix):
        return False
    return True


def _candidate_scores(index, candidate_indices: list[int], query_vector: np.ndarray) -> np.ndarray:
    import numpy as np

    identifiers = np.asarray(candidate_indices, dtype="int64")
    if hasattr(index, "reconstruct_batch"):
        vectors = index.reconstruct_batch(identifiers)
    else:
        vectors = np.vstack([index.reconstruct(int(identifier)) for identifier in identifiers])
    return vectors @ query_vector


def search_ais_hybrid(
    query: str,
    faiss_path: Path,
    docs_path: Path,
    model: str,
    base_url: str,
    timeout: int,
    top_k: int,
) -> list[dict]:
    import numpy as np

    if top_k <= 0:
        raise ValueError("top_k must be positive")

    index, documents = _load_resources(str(faiss_path.resolve()), str(docs_path.resolve()))
    filters, expanded_query = parse_ais_query(query)
    candidates = [index for index, doc in enumerate(documents) if _matches(doc, filters)]
    if not candidates:
        return []

    vector = np.asarray(embed_text(expanded_query, model, base_url, timeout), dtype="float32")
    vector /= max(float(np.linalg.norm(vector)), 1e-12)
    scores = _candidate_scores(index, candidates, vector)
    ranked = list(zip(candidates, scores.tolist()))
    if filters.sort_by_duration:
        ranked.sort(
            key=lambda item: (_as_float(documents[item[0]].get("duration_minutes")), item[1]),
            reverse=True,
        )
    else:
        ranked.sort(key=lambda item: item[1], reverse=True)

    results = []
    for document_index, score in ranked[:top_k]:
        doc = documents[document_index]
        results.append(
            {
                "score": float(score),
                "query": query,
                "expanded_query": expanded_query,
                "chunk_id": doc.get("chunk_id") or doc.get("event_id"),
                "source": doc.get("source"),
                "page": None,
                "text": doc["text"],
                "document": doc,
                "kind": "ais",
                "structured_filters": {
                    "event_types": list(filters.event_types),
                    "min_duration_minutes": filters.min_duration_minutes,
                    "max_duration_minutes": filters.max_duration_minutes,
                    "mmsi": filters.mmsi,
                    "date_prefix": filters.date_prefix,
                    "sort_by_duration": filters.sort_by_duration,
                },
            }
        )
    return results
