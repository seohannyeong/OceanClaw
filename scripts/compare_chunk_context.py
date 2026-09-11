"""PDF bookmark titles and bounded same-section neighbors: BGE-M3 ablation."""
import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from time import perf_counter

import faiss
import numpy as np
from pypdf import PdfReader

from compare_retrieval import ROOT, digest, load_benchmark, load_index, normalized, ollama_snapshot, write_json
from oceanclaw import config
from oceanclaw.ollama_embed import embed_text


from oceanclaw.manual_titles import compact, bookmarks, annotate


def contexts(seeds, documents):
    lookup = {d["chunk_id"]: i for i, d in enumerate(documents)}
    output = [{"chunk_id": d["chunk_id"], "text": d["text"], "kind": "seed"} for d in seeds]
    seen = {(d["chunk_id"], None) for d in seeds}
    for seed in seeds:
        position = lookup[seed["chunk_id"]]
        section_ids = {s["section_id"] for s in seed["sections"]}
        for neighbor_pos in (position - 1, position + 1):
            if not 0 <= neighbor_pos < len(documents):
                continue
            neighbor = documents[neighbor_pos]
            if (neighbor["source"], neighbor["page"]) != (seed["source"], seed["page"]):
                continue
            if (neighbor["chunk_id"], None) in seen:
                continue
            for part in neighbor["sections"]:
                key = (neighbor["chunk_id"], part["section_id"])
                if part["section_id"] in section_ids and key not in seen:
                    output.append({"chunk_id": neighbor["chunk_id"], "text": part["text"], "kind": "neighbor", "section_id": part["section_id"]})
                    seen.add(key)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    paths, fingerprints, original, questions = load_benchmark()
    lock = json.loads((ROOT / "data/eval/benchmark.lock.json").read_text(encoding="utf-8"))
    if lock != {k: v["sha256"] for k, v in fingerprints.items()}:
        raise ValueError("Frozen inputs changed")
    base = ROOT / "index/bge_m3"
    metadata = json.loads((base / "pdf_docs.json").read_text(encoding="utf-8"))
    if metadata["documents"] != original["documents"] or metadata["model"] != "bge-m3":
        raise ValueError("BGE baseline mismatch")
    for key, path in (("bge_index", base / "pdf.faiss"), ("bge_docs", base / "pdf_docs.json"), ("pdf", config.PDF_PATH)):
        paths[key] = path
        fingerprints[key] = {"path": str(path), "sha256": digest(path)}
    previous = json.loads((ROOT / "output/eval/20260910_211707_618252/manifest.json").read_text(encoding="utf-8"))
    installed = ollama_snapshot(config.OLLAMA_BASE_URL, "tags")
    old = {m["name"]: m["digest"] for m in previous["installed_models"]["models"]}
    current = {m["name"]: m["digest"] for m in installed.get("models", [])}
    if current.get("bge-m3:latest") != old.get("bge-m3:latest") or "bge-m3:latest" not in current:
        raise ValueError("BGE model digest changed or unavailable")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = ROOT / "output/eval" / f"chunk_context_{stamp}"
    out.mkdir(parents=True)
    index_dir = ROOT / "index" / f"bge_m3_titles_{stamp}"
    index_dir.mkdir()
    pages = [json.loads(line) for line in paths["pages"].read_text(encoding="utf-8").splitlines() if line.strip()]
    docs, missing = annotate(pages, original["documents"], bookmarks(PdfReader(config.PDF_PATH)))
    write_json(out / "heading_audit.json", {"unmatched_bookmarks": missing, "chunks_without_title": [d["chunk_id"] for d in docs if not d["sections"]]})
    with (out / "titled_chunks.jsonl").open("w", encoding="utf-8") as handle:
        for doc in docs:
            handle.write(json.dumps(doc, ensure_ascii=False) + "\n")
    vectors = []
    for number, doc in enumerate(docs, 1):
        vector = np.asarray(embed_text(doc["embedding_text"], "bge-m3", config.OLLAMA_BASE_URL, args.timeout), dtype="float32")
        if vector.shape != (1024,) or not np.isfinite(vector).all() or not np.linalg.norm(vector):
            raise ValueError("Invalid embedding")
        vectors.append(vector)
        if number % 30 == 0:
            print(f"Embedding {number}/{len(docs)}", flush=True)
    matrix = np.asarray(vectors)
    faiss.normalize_L2(matrix)
    titled = faiss.IndexFlatIP(matrix.shape[1])
    titled.add(matrix)
    (index_dir / "pdf.faiss").write_bytes(faiss.serialize_index(titled).tobytes())
    write_json(index_dir / "pdf_docs.json", {"model": "bge-m3", "model_digest": current["bge-m3:latest"], "vector_dim": 1024,
        "text_field": "embedding_text", "documents": docs, "input_hashes": fingerprints})
    baseline = load_index(base / "pdf.faiss", metadata)
    write_json(out / "manifest.json", {"inputs": fingerprints, "models": installed, "new_index": str(index_dir),
        "code_sha256": digest(Path(__file__)), "policy": "PDF outline title paths, all original chunk bodies/IDs retained; adjacent radius=1, same page and section, neighbor text clipped to section. No translation/expansion. No answer generation.",
        "timing": "Same question vector shared by both indexes; no cold-start comparison; context metrics allow more than 3 chunks. Evaluation questions were previously inspected."})
    rows = []
    with (out / "results.jsonl").open("w", encoding="utf-8") as stream:
        for q in questions:
            tick = perf_counter()
            vector = np.asarray([embed_text(q["question"], "bge-m3", config.OLLAMA_BASE_URL, args.timeout)], dtype="float32")
            if vector.shape != (1, 1024) or not np.isfinite(vector).all() or not np.linalg.norm(vector):
                raise ValueError("Invalid query embedding")
            faiss.normalize_L2(vector)
            embedding_seconds = perf_counter() - tick
            for mode, index in (("baseline", baseline), ("titles", titled)):
                tick = perf_counter()
                scores, ids = index.search(vector, 3)
                seeds = [docs[int(i)] for i in ids[0]]
                ranks = [rank for rank, doc in enumerate(seeds, 1) if doc["chunk_id"] in q["relevant_chunk_ids"]]
                expanded = contexts(seeds, docs)
                covered = any(c["chunk_id"] in q["relevant_chunk_ids"] and normalized(q["evidence"]) in normalized(c["text"]) for c in expanded)
                row = {"id": q["id"], "question": q["question"], "group": q["group"], "mode": mode,
                    "hit_at_3": bool(ranks), "reciprocal_rank": 1/ranks[0] if ranks else 0,
                    "context_hit": covered, "context_chars": sum(len(c["text"]) for c in expanded),
                    "seed_chars": sum(len(d["text"]) for d in seeds), "context_piece_count": len(expanded),
                    "embedding_seconds": embedding_seconds, "search_and_context_seconds": perf_counter()-tick,
                    "top3": [{"rank": rank, "score": float(score), **doc} for rank, (score, doc) in enumerate(zip(scores[0], seeds), 1)], "context": expanded}
                rows.append(row)
                stream.write(json.dumps(row, ensure_ascii=False)+"\n")
                stream.flush()
            print(f"{q['id']}: baseline={rows[-2]['hit_at_3']} titles={rows[-1]['hit_at_3']} context={rows[-1]['context_hit']}", flush=True)
    summary = []
    for mode in ("baseline", "titles"):
        subset = [r for r in rows if r["mode"] == mode]
        summary.append({"mode": mode, "questions": len(subset), "hits_at_3": sum(r["hit_at_3"] for r in subset),
            "mrr_at_3": sum(r["reciprocal_rank"] for r in subset)/len(subset), "context_hits": sum(r["context_hit"] for r in subset),
            "mean_seed_chars": sum(r["seed_chars"] for r in subset)/len(subset),
            "mean_context_chars": sum(r["context_chars"] for r in subset)/len(subset),
            "mean_context_pieces": sum(r["context_piece_count"] for r in subset)/len(subset)})
    write_json(out / "summary.json", summary)
    changed = [k for k, path in paths.items() if digest(path) != fingerprints[k]["sha256"]]
    write_json(out / "integrity.json", {"unchanged": not changed, "changed": changed})
    print(json.dumps(summary, indent=2), flush=True)
    print(out, flush=True)
    return int(bool(changed))


if __name__ == "__main__":
    raise SystemExit(main())
