"""Replay shared failures with saved translations; never change benchmark labels."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from time import perf_counter

import faiss
import numpy as np

from compare_retrieval import ROOT, digest, load_benchmark, load_index, normalized, ollama_snapshot, read_jsonl, write_json
from oceanclaw import config
from oceanclaw.ollama_embed import embed_text

# Human translations used only as diagnostic probes, not benchmark replacements.
PROBES = {
    "q06": "When replacing the engine oil filter, how much further should I turn it after the seal makes contact?",
    "q11": "Can I check the engine oil level while the engine is running?",
    "q13": "What should I moisten the new fuel filter seal with before installing it?",
    "q14": "Can I top up a battery with tap water if its electrolyte level is low?",
    "q16": "When fitting a new engine oil filter, how many more turns are needed after the seal ring makes contact?",
    "q18": "Can I disconnect the battery while the engine is running?",
    "q26": "What is the specified exhaust valve clearance?",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=ROOT / "output/eval/20260910_211707_618252")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    run = config.project_path(str(args.run))
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["inputs"].values():
        if digest(Path(entry["path"])) != entry["sha256"]:
            raise ValueError(f"Input changed: {entry['path']}")
    _, _, _, questions = load_benchmark()
    rows = read_jsonl(run / "results.jsonl")
    saved = {(r["id"], r["mode"]): r for r in rows}
    failed = [q for q in questions if all(saved[q["id"], mode]["status"] == "ok" and not saved[q["id"], mode]["hit_at_3"] for mode in ("translated", "multilingual"))]
    indexes = {}
    for mode, index_key, docs_key in (("translated", "index", "docs"), ("multilingual", "multilingual_index", "multilingual_docs")):
        metadata = json.loads(Path(manifest["inputs"][docs_key]["path"]).read_text(encoding="utf-8"))
        indexes[mode] = (load_index(Path(manifest["inputs"][index_key]["path"]), metadata), metadata)
    current_models = ollama_snapshot(config.OLLAMA_BASE_URL, "tags")
    old_digests = {m["name"]: m["digest"] for m in manifest["installed_models"]["models"]}
    current_digests = {m["name"]: m["digest"] for m in current_models.get("models", [])}
    for _, metadata in indexes.values():
        name = metadata["model"]
        name = name if ":" in name else name + ":latest"
        if name not in current_digests or old_digests.get(name) != current_digests[name]:
            raise ValueError(f"Embedding model changed or unavailable: {name}")
    out = ROOT / "output/eval" / ("failure_audit_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    out.mkdir(parents=True)
    write_json(out / "manifest.json", {"parent_run": str(run), "inputs": manifest["inputs"], "models": current_models,
        "question_ids": [q["id"] for q in failed], "probes": PROBES,
        "note": "Saved queries replayed. Full ranking used to locate strict gold, top10 text saved. Human translations are post-hoc diagnostics, not new benchmark scores."})
    report = []
    with (out / "results.jsonl").open("w", encoding="utf-8") as stream:
        for q in failed:
            for mode in ("translated", "multilingual"):
                index, metadata = indexes[mode]
                variants = [("saved", saved[q["id"], mode]["search_query"])]
                if q["id"] in PROBES and mode == "translated":
                    variants.append(("human_translation_probe", PROBES[q["id"]]))
                for variant, query in variants:
                    start = perf_counter()
                    vector = np.asarray([embed_text(query, metadata["model"], config.OLLAMA_BASE_URL, args.timeout)], dtype="float32")
                    if vector.shape != (1, index.d) or not np.isfinite(vector).all() or not np.linalg.norm(vector):
                        raise ValueError("Invalid query embedding")
                    faiss.normalize_L2(vector)
                    scores, ids = index.search(vector, index.ntotal)
                    ranked = [{"rank": rank, "score": float(score), **metadata["documents"][int(idx)]} for rank, (score, idx) in enumerate(zip(scores[0], ids[0]), 1)]
                    gold = [r for r in ranked if r["chunk_id"] in q["relevant_chunk_ids"]]
                    row = {"id": q["id"], "question": q["question"], "mode": mode, "variant": variant, "query": query,
                        "gold": gold, "gold_rank": gold[0]["rank"], "top10": ranked[:10], "seconds": perf_counter()-start,
                        "same_top3_as_previous": [r["chunk_id"] for r in ranked[:3]] == [r["chunk_id"] for r in saved[q["id"], mode]["results"]] if variant == "saved" else None}
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stream.flush()
                    report.append({k: row[k] for k in ("id", "mode", "variant", "gold_rank", "same_top3_as_previous")})
                    print(report[-1], flush=True)
    write_json(out / "ranks.json", report)
    chunks = indexes["translated"][1]["documents"]
    write_json(out / "context.json", [{"question": q, "expected_page_chunks": [c for c in chunks if c["page"] == q["page"]],
        "same_evidence_elsewhere": [c for c in chunks if normalized(q["evidence"]) in normalized(c["text"]) and c["page"] != q["page"]]} for q in failed])
    changed = [name for name, entry in manifest["inputs"].items() if digest(Path(entry["path"])) != entry["sha256"]]
    write_json(out / "integrity.json", {"unchanged": not changed, "changed": changed})
    print(out, flush=True)
    return int(bool(changed))


if __name__ == "__main__":
    raise SystemExit(main())
