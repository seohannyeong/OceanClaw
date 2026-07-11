"""FAISS 기반 간단 벡터 저장소 (코사인 유사도)."""

from __future__ import annotations

import json
from typing import Dict, List, Tuple

import numpy as np


class VectorStore:
    def __init__(self, index, docs: List[Dict]):
        self.index = index
        self.docs = docs

    @classmethod
    def build(cls, docs: List[Dict], embeddings: List[List[float]]) -> "VectorStore":
        import faiss

        mat = np.asarray(embeddings, dtype="float32")
        faiss.normalize_L2(mat)  # 정규화 후 내적 = 코사인 유사도
        index = faiss.IndexFlatIP(mat.shape[1])
        index.add(mat)
        return cls(index, docs)

    def search(self, query_vec: List[float], k: int) -> List[Tuple[Dict, float]]:
        import faiss

        if not self.docs:
            return []
        q = np.asarray([query_vec], dtype="float32")
        faiss.normalize_L2(q)
        scores, idx = self.index.search(q, min(k, len(self.docs)))
        hits: List[Tuple[Dict, float]] = []
        for rank, doc_i in enumerate(idx[0]):
            if doc_i == -1:
                continue
            hits.append((self.docs[doc_i], float(scores[0][rank])))
        return hits

    def save(self, prefix: str) -> None:
        import faiss

        faiss.write_index(self.index, prefix + ".faiss")
        with open(prefix + ".json", "w", encoding="utf-8") as f:
            json.dump(self.docs, f, ensure_ascii=False)

    @classmethod
    def load(cls, prefix: str) -> "VectorStore":
        import faiss

        index = faiss.read_index(prefix + ".faiss")
        with open(prefix + ".json", encoding="utf-8") as f:
            docs = json.load(f)
        return cls(index, docs)
