"""Freeze new questions and evaluate fixed retrieval or collect /ask responses."""
import argparse
import json
import platform
import re
import statistics
import shutil
import subprocess
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from time import perf_counter

import faiss
import numpy as np

from compare_retrieval import ROOT, PROMPT, digest, load_index, normalized, read_jsonl, write_json, ollama_snapshot
from oceanclaw import config
from oceanclaw.contextual_manual import extend_context
from oceanclaw.ollama_chat import chat
from oceanclaw.ollama_embed import embed_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", help="Collect real /ask responses instead of retrieval-only evaluation")
    parser.add_argument("--require-jetson", action="store_true")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--modes", nargs="+", choices=["translated", "multilingual", "titles"], default=["translated", "titles"])
    args = parser.parse_args()
    if not 1 <= args.limit <= 15 or not 1 <= args.repeats <= 10:
        parser.error("limit must be 1..15 and repeats 1..10")
    device_path = Path("/proc/device-tree/model")
    device = device_path.read_text().strip("\x00") if device_path.exists() else platform.platform()
    if args.require_jetson and "jetson" not in device.lower():
        raise ValueError("This is not a Jetson. No Jetson result will be fabricated.")
    if args.require_jetson and (not args.api_url or urllib.parse.urlparse(args.api_url).hostname not in {"localhost", "127.0.0.1"}):
        raise ValueError("Measure Jetson locally with --api-url http://127.0.0.1:8000")
    questions_path = ROOT / "data/eval/manual_holdout_v1.jsonl"
    questions = read_jsonl(questions_path)
    old = read_jsonl(ROOT / "data/eval/manual_queries.jsonl")
    pages = read_jsonl(config.PDF_PAGES_PATH)
    base_meta = json.loads(config.PDF_DOCS_PATH.read_text(encoding="utf-8"))
    title_dir = config.project_path(config.TITLED_MANUAL_INDEX_DIR)
    title_meta = json.loads((title_dir / "pdf_docs.json").read_text(encoding="utf-8"))
    multilingual_path = ROOT / "index/bge_m3/pdf.faiss"
    multilingual_docs = ROOT / "index/bge_m3/pdf_docs.json"
    multilingual_meta = json.loads(multilingual_docs.read_text(encoding="utf-8")) if "multilingual" in args.modes else None
    for q in questions:
        if q["page"] in {x["page"] for x in old}:
            raise ValueError("Holdout page overlaps development questions")
        if not any(p["page"] == q["page"] and normalized(q["evidence"]) in normalized(p["text"]) for p in pages):
            raise ValueError(f"Missing page evidence: {q['id']}")
        q["relevant_chunk_ids"] = [d["chunk_id"] for d in base_meta["documents"] if d["page"] == q["page"] and normalized(q["evidence"]) in normalized(d["text"])]
        if not q["relevant_chunk_ids"]:
            raise ValueError(f"Missing chunk evidence: {q['id']}")
    frozen = {"questions": digest(questions_path), "pages": digest(config.PDF_PAGES_PATH), "chunks": digest(config.PDF_CHUNKS_PATH),
        "base_index": digest(config.PDF_FAISS_PATH), "title_index": digest(title_dir / "pdf.faiss"), "title_docs": digest(title_dir / "pdf_docs.json")}
    lock_path = ROOT / "data/eval/holdout_v1.lock.json"
    if lock_path.exists() and json.loads(lock_path.read_text(encoding="utf-8")) != frozen:
        raise ValueError("Holdout inputs changed")
    if not lock_path.exists():
        write_json(lock_path, frozen)
    out = ROOT / "output/eval" / (("ask_benchmark_" if args.api_url else "holdout_") + datetime.now().strftime("%Y%m%d_%H%M%S"))
    out.mkdir(parents=True)
    write_json(out / "manifest.json", {"device": device, "platform": platform.platform(), "inputs": frozen,
        "api_url": args.api_url, "models": ollama_snapshot(config.OLLAMA_BASE_URL, "tags"),
        "limit": args.limit, "repeats": args.repeats, "max_context_chars": 5000,
        "modes": args.modes, "multilingual_index_sha256": digest(multilingual_path) if multilingual_meta else None,
        "multilingual_docs_sha256": digest(multilingual_docs) if multilingual_meta else None,
        "note": "New questions after development, same manual, disjoint answer pages. Not external blind evaluation. No tuning after results. First repeat may include cold starts. Answer correctness requires manual review."})
    telemetry = None
    log = None
    if args.require_jetson:
        executable = shutil.which("tegrastats")
        if not executable:
            raise RuntimeError("tegrastats unavailable; install/enable it before Jetson measurement")
        log = (out / "tegrastats.log").open("w", encoding="utf-8")
        telemetry = subprocess.Popen([executable, "--interval", "500"], stdout=log, stderr=subprocess.STDOUT)
    rows = []
    try:
        indexes = {} if args.api_url else {"translated": load_index(config.PDF_FAISS_PATH, base_meta), "titles": load_index(title_dir / "pdf.faiss", title_meta)}
        if multilingual_meta and not args.api_url:
            indexes["multilingual"] = load_index(multilingual_path, multilingual_meta)
        with (out / "results.jsonl").open("w", encoding="utf-8") as handle:
            for repeat in range(args.repeats):
                for q in questions[:args.limit]:
                    modes = ("titles", "titles_neighbors") if args.api_url else args.modes
                    if repeat % 2:
                        modes = tuple(reversed(modes))
                    for mode in modes:
                        row = {"id": q["id"], "question": q["question"], "mode": mode, "repeat": repeat, "status": "error", "hit": False}
                        start = perf_counter()
                        try:
                            if args.api_url:
                                payload = {"question": q["question"], "route": "manual", "manual_profile": mode, "top_k": 3, "max_context_chars": 5000, "save_log": False}
                                request = urllib.request.Request(args.api_url.rstrip("/") + "/ask", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
                                with urllib.request.urlopen(request, timeout=args.timeout) as response:
                                    result = json.load(response)
                                if result.get("manual_profile") != mode:
                                    raise ValueError("Server does not support requested profile; deploy updated API")
                                row["response"] = result
                                row["hit"] = any(d["chunk_id"] in q["relevant_chunk_ids"] and normalized(q["evidence"]) in normalized(d["text"]) for d in result["results"])
                                row["answer_review"] = "pending"
                            else:
                                query = q["question"]
                                metadata = title_meta
                                if mode == "multilingual":
                                    metadata = multilingual_meta
                                if mode == "translated":
                                    query = chat([{"role": "system", "content": PROMPT}, {"role": "user", "content": query}], config.OLLAMA_CHAT_MODEL, config.OLLAMA_BASE_URL, args.timeout, temperature=0)
                                    metadata = base_meta
                                row["search_query"] = query
                                vector = np.asarray([embed_text(query, metadata["model"], config.OLLAMA_BASE_URL, args.timeout)], dtype="float32")
                                if vector.shape != (1,indexes[mode].d) or not np.isfinite(vector).all() or not np.linalg.norm(vector):
                                    raise ValueError("Invalid embedding")
                                faiss.normalize_L2(vector)
                                scores, ids = indexes[mode].search(vector, 3)
                                seeds = [metadata["documents"][int(i)] for i in ids[0]]
                                row["top3"] = [{"score": float(s), **d} for s, d in zip(scores[0], seeds)]
                                row["hit"] = any(d["chunk_id"] in q["relevant_chunk_ids"] for d in seeds)
                                if mode == "titles":
                                    pieces = extend_context(seeds, metadata["documents"], 5000)
                                    row["context"] = pieces
                                    row["context_hit"] = any(p["document"]["chunk_id"] in q["relevant_chunk_ids"] and normalized(q["evidence"]) in normalized(p["text"]) for p in pieces)
                            row["status"] = "ok"
                        except Exception as exc:
                            row["error"] = f"{type(exc).__name__}: {exc}"
                        row["seconds"] = perf_counter() - start
                        row["ollama_memory"] = ollama_snapshot(config.OLLAMA_BASE_URL)
                        rows.append(row)
                        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                        handle.flush()
                        print(q["id"], mode, row["status"], row["hit"], flush=True)
    finally:
        if telemetry:
            telemetry.terminate()
            telemetry.wait(timeout=5)
            log.close()
    write_json(out / "summary.json", [{"mode": mode, "requests": len([r for r in rows if r["mode"] == mode]),
        "hits": sum(r["hit"] for r in rows if r["mode"] == mode), "errors": sum(r["status"] != "ok" for r in rows if r["mode"] == mode),
        "context_hits": sum(r.get("context_hit", False) for r in rows if r["mode"] == mode),
        "median_seconds": statistics.median(r["seconds"] for r in rows if r["mode"] == mode),
        "max_seconds": max(r["seconds"] for r in rows if r["mode"] == mode)} for mode in sorted({r["mode"] for r in rows})])
    if args.require_jetson:
        samples = re.findall(r"RAM (\d+)/(\d+)MB", (out / "tegrastats.log").read_text(encoding="utf-8"))
        write_json(out / "memory_summary.json", {"sample_count": len(samples),
            "sampled_peak_system_ram_mb": max((int(s[0]) for s in samples), default=None),
            "note": "Whole-device RAM sampled every 500ms, not process RSS or guaranteed instantaneous peak."})
    print(out, flush=True)
    return int(any(r["status"] != "ok" for r in rows))


if __name__ == "__main__":
    raise SystemExit(main())
