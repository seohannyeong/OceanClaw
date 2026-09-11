"""Default titled BGE-M3 manual retrieval; optional same-section neighbors."""
import json

import faiss
import numpy as np

from . import config
from .ollama_embed import embed_text


def extend_context(seeds, documents, max_chars=5000):
    lookup = {d["chunk_id"]: i for i, d in enumerate(documents)}
    pieces = []
    seen = set()
    used = 0

    def add(doc, text, role, section_id=None):
        nonlocal used
        key = (doc["chunk_id"], section_id)
        if key in seen or (doc["chunk_id"], None) in seen or used + len(text) > max_chars:
            return
        pieces.append({"document": doc, "text": text, "context_role": role, "section_id": section_id})
        seen.add(key)
        used += len(text)

    for seed in seeds:
        add(seed, seed["text"], "seed")
    for seed in seeds:
        if (seed["chunk_id"], None) not in seen:
            continue
        ids = {s["section_id"] for s in seed.get("sections", [])}
        at = lookup[seed["chunk_id"]]
        for i in (at - 1, at + 1):
            if not 0 <= i < len(documents):
                continue
            doc = documents[i]
            if (doc["source"], doc["page"]) != (seed["source"], seed["page"]):
                continue
            for section in doc.get("sections", []):
                if section["section_id"] in ids:
                    add(doc, section["text"], "neighbor", section["section_id"])
    return pieces


def search_contextual_manual(question, top_k, neighbors=False, min_score=0, max_chars=5000,
                             directory=None, base_url=None, timeout=None):
    directory = config.project_path(directory or config.TITLED_MANUAL_INDEX_DIR)
    if top_k < 1:
        raise ValueError("top_k must be positive")
    if not (directory / "pdf_docs.json").exists() or not (directory / "pdf.faiss").exists():
        raise FileNotFoundError(f"Titled BGE-M3 index missing: {directory}. Copy the titled index or rebuild it; no legacy fallback is used.")
    metadata = json.loads((directory / "pdf_docs.json").read_text(encoding="utf-8"))
    if metadata.get("model", "").split(":")[0] != "bge-m3" or metadata.get("text_field") != "embedding_text":
        raise ValueError("Expected a titled BGE-M3 index (text_field=embedding_text)")
    documents = metadata["documents"]
    index = faiss.deserialize_index(np.frombuffer((directory / "pdf.faiss").read_bytes(), dtype="uint8"))
    if index.ntotal != len(documents) or index.d != metadata["vector_dim"]:
        raise ValueError("Titled index metadata mismatch")
    vector = np.asarray([embed_text(question, metadata["model"], base_url or config.OLLAMA_BASE_URL,
                                   timeout or config.OLLAMA_TIMEOUT)], dtype="float32")
    if vector.shape != (1, index.d) or not np.isfinite(vector).all() or not np.linalg.norm(vector):
        raise ValueError("Invalid embedding")
    faiss.normalize_L2(vector)
    scores, ids = index.search(vector, top_k)
    ranked = [(documents[int(i)], float(score)) for i, score in zip(ids[0], scores[0]) if i >= 0 and score >= min_score]
    seeds = [doc for doc, _ in ranked]
    score_map = {doc["chunk_id"]: score for doc, score in ranked}
    pieces = extend_context(seeds, documents, max_chars) if neighbors else []
    if not neighbors:
        pieces = []
        used = 0
        for doc in seeds:
            if used + len(doc["text"]) <= max_chars:
                pieces.append({"document": doc, "text": doc["text"], "context_role": "seed", "section_id": None})
                used += len(doc["text"])
    results = []
    for piece in pieces:
        doc = piece["document"]
        results.append({"kind": "manual", "query": question, "expanded_query": question,
            "source": doc["source"], "page": doc["page"], "chunk_id": doc["chunk_id"],
            "text": piece["text"], "document": doc, "context_role": piece["context_role"],
            "section_id": piece["section_id"], "score": score_map.get(doc["chunk_id"]),
            "title_paths": [s["title_path"] for s in doc.get("sections", [])
                            if piece["section_id"] is None or s["section_id"] == piece["section_id"]]})
    return results
