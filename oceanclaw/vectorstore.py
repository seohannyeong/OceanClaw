"""FAISS vector store utilities."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from socket import timeout
from typing import Dict, List

import faiss
import numpy as np

from .ollama_embed import embed_text
from .query_expansion import expand_query


def load_jsonl(path: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_csv_docs(path: Path, id_field: str = "event_id") -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for index, row in enumerate(reader):
            doc = dict(row)
            doc["chunk_id"] = row.get(id_field) or f"row-{index}"
            rows.append(doc)
    return rows


def normalize_vectors(vectors: list[list[float]]) -> np.ndarray:
    array = np.array(vectors, dtype="float32")
    faiss.normalize_L2(array)
    return array


def build_faiss_index(
    chunks_path: Path,
    faiss_path: Path,
    docs_path: Path,
    model: str,
    base_url: str,
    timeout: int,
) -> int:
    chunks = load_jsonl(chunks_path)
    if not chunks:
        raise ValueError(f"No chunks found: {chunks_path}")

    vectors: list[list[float]] = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_id = str(chunk["chunk_id"])
        print(f"Embedding {index}/{len(chunks)}: {chunk_id}")
        vectors.append(embed_text(str(chunk["text"]), model, base_url, timeout))

    matrix = normalize_vectors(vectors)
    faiss_index = faiss.IndexFlatIP(matrix.shape[1])
    faiss_index.add(matrix)

    faiss_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = faiss.serialize_index(faiss_index)
    with faiss_path.open("wb") as f:
        f.write(serialized.tobytes())

    metadata = {
        "model": model,
        "source_chunks": str(chunks_path),
        "vector_dim": int(matrix.shape[1]),
        "documents": chunks,
    }
    with docs_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return len(chunks)


def build_docs_faiss_index(
    documents: list[dict],
    source_path: Path,
    faiss_path: Path,
    docs_path: Path,
    model: str,
    base_url: str,
    timeout: int,
    text_field: str = "text",
) -> int:
    if not documents:
        raise ValueError(f"No documents found: {source_path}")

    vectors: list[list[float]] = []
    for index, doc in enumerate(documents, start=1):
        doc_id = str(doc.get("chunk_id") or doc.get("event_id") or index)
        print(f"Embedding {index}/{len(documents)}: {doc_id}")
        vectors.append(embed_text(str(doc[text_field]), model, base_url, timeout))

    matrix = normalize_vectors(vectors)
    faiss_index = faiss.IndexFlatIP(matrix.shape[1])
    faiss_index.add(matrix)

    faiss_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = faiss.serialize_index(faiss_index)
    with faiss_path.open("wb") as f:
        f.write(serialized.tobytes())

    metadata = {
        "model": model,
        "source": str(source_path),
        "vector_dim": int(matrix.shape[1]),
        "text_field": text_field,
        "documents": documents,
    }
    with docs_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return len(documents)


def search_faiss_index(
    query: str,
    faiss_path: Path,
    docs_path: Path,
    model: str,
    base_url: str,
    timeout: int,
    top_k: int,
) -> list[dict]:
    if not faiss_path.exists():
        raise FileNotFoundError(f"FAISS index not found: {faiss_path}")
    if not docs_path.exists():
        raise FileNotFoundError(f"Docs metadata not found: {docs_path}")

    with faiss_path.open("rb") as f:
        serialized = np.frombuffer(f.read(), dtype="uint8")
    faiss_index = faiss.deserialize_index(serialized)
    with docs_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)

    expanded_query = expand_query(query)
    #expanded_query = query
    query_vector = normalize_vectors([embed_text(expanded_query, model, base_url, timeout)])
    scores, indices = faiss_index.search(query_vector, top_k)
    documents = metadata["documents"]

    results: list[dict] = []
    for score, index in zip(scores[0], indices[0]):
        if index < 0:
            continue
        doc = documents[int(index)]
        results.append(
            {
                "score": float(score),
                "query": query,
                "expanded_query": expanded_query,
                "chunk_id": doc.get("chunk_id") or doc.get("event_id"),
                "source": doc.get("source"),
                "page": doc.get("page"),
                "text": doc["text"],
                "document": doc,
            }
        )
    return results
