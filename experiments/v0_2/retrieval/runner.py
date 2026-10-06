"""分阶段执行：dev → lock CONFIG → test；不覆盖第一次正式结果。"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter
import traceback
import httpx
from experiments.v0_2.datasets import load_bundle, validate_bundle, RETRIEVAL_CATEGORIES
from .backends import DenseBackend, HybridBackend
from .bm25 import BM25Backend
from .metrics import distributions, query_metrics, summarize
from .tokenizer import VERSION

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT/"experiments/v0_2/retrieval/CONFIG.json"
SETTINGS = {
    "experiment_version": "v0.2-retrieval-1",
    "tokenizer_version": VERSION,
    "bm25_k1": 1.5, "bm25_b": .75,
    "bm25_query_terms": "unique; no query frequency multiplier",
    "bm25_zero_overlap": "return zero scores; chunk_id ascending tie",
    "rrf_k": 60, "candidate_pool_size": 20,
    "rrf_tie": "chunk_id ascending",
    "embedding_model": "nomic-embed-text",
    "ollama_url": "http://localhost:11434",
    "timeout_seconds": 120,
    "faiss_index_type": "IndexFlatIP", "normalized": True,
    "top_k_settings": [1, 3, 5],
    "test_latency_repeats": 3, "dev_latency_repeats": 1,
    "warmup_queries_per_backend_per_split": 1,
    "query_order": "frozen dataset order; fixed dense,bm25,hybrid order per query",
    "query_embedding_cache": False,
    "metric_primary_run": 1,
    "bad_case_correctness": "complete evidence coverage at K=3; no-answer excluded",
}
BACKENDS = ("dense", "bm25", "hybrid")

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refuse to overwrite: {path.name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8", newline="\n")

def source_hashes(root=ROOT):
    files = list((root/"experiments/v0_2/retrieval").glob("*.py"))
    files += [root/"scripts/v0_2/run_retrieval.py", root/"tests/v0_2/test_retrieval.py"]
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(files)}

def protected_hashes(root=ROOT):
    tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
    files = {root/name for name in tracked if name and (root/name).is_file()}
    for folder in ("store", "docs/evidence"):
        files.update(p for p in (root/folder).rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts and p.suffix != ".pyc")
    files.update(p for p in (root/"eval").glob("*baseline*.json"))
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(files)}

def verify_integrity(expected=None, root=ROOT):
    frozen = json.loads((root/"docs/releases/frozen_core.json").read_text())
    bad = [f for f, h in frozen.items() if digest(root/f) != h]
    bundle = load_bundle(root)
    validated = validate_bundle(bundle, root)
    if bad or not validated["valid"]:
        raise ValueError(f"frozen integrity failed: {bad + validated['errors']}")
    tag = subprocess.check_output(["git", "-C", str(root), "rev-list", "-n", "1",
                                   "v0.1-agentic-rag-baseline"]).decode().strip()
    if tag != "aa422d826fa484933d9949c16fc79e1a2f22eda1":
        raise ValueError("V0.1 tag changed")
    current = protected_hashes(root)
    if expected is not None and current != expected:
        raise ValueError("protected tracked/evidence/index files changed")
    nanobot = root.parent/"nanobot"
    status = subprocess.check_output(["git", "-C", str(nanobot), "status", "--porcelain"]).decode()
    if status:
        raise ValueError("nanobot repo not clean")
    return bundle, current

def model_metadata(settings):
    response = httpx.get(settings["ollama_url"]+"/api/tags", timeout=30)
    response.raise_for_status()
    models = [m for m in response.json()["models"] if m["name"].split(":")[0] == settings["embedding_model"]]
    if len(models) != 1:
        raise ValueError("expected one installed nomic-embed-text model")
    version = httpx.get(settings["ollama_url"]+"/api/version", timeout=30)
    version.raise_for_status()
    return {"embedding_model": {k: models[0].get(k) for k in ("name", "digest", "size")},
            "ollama_version": version.json()["version"]}

def make_backends(run_dir, settings, bundle, build):
    dense = DenseBackend(ROOT, run_dir/"index", settings, bundle["config"])
    stats = dense.ingest(bundle["corpus"]["chunks"]) if build else dense.load()
    if stats["ntotal"] != len(bundle["corpus"]["chunks"]):
        raise ValueError("V0.2 index count mismatch")
    metadata = dense.adapter.store._chunks
    expected = bundle["corpus"]["chunks"]
    if [(c["chunk_id"], c["text"], c["source_file"], c.get("page")) for c in metadata] != [
        (c["chunk_id"], c["text"], c["source"], c.get("page")) for c in expected]:
        raise ValueError("V0.2 persisted metadata differs from frozen corpus")
    bm25 = BM25Backend(expected, settings["bm25_k1"], settings["bm25_b"])
    return {"dense": dense, "bm25": bm25,
            "hybrid": HybridBackend(dense, bm25, settings["candidate_pool_size"], settings["rrf_k"])}, stats

def evaluate(backends, items, repeats):
    records = {name: [] for name in BACKENDS}
    warmup = {}
    # 每种方法先运行一个真实query；warm-up不纳入latency统计。
    for name in BACKENDS:
        start = perf_counter()
        backends[name].search(items[0]["query"], 5)
        warmup[name] = {"query_id": items[0]["id"], "wall_ms": (perf_counter()-start)*1000,
                        **backends[name].last_latency}
    for item in items:
        runs = {name: [] for name in BACKENDS}
        # 顺序固定。Dense/Hybrid各自独立计算query embedding，不复用缓存。
        for repeat in range(1, repeats+1):
            for name in BACKENDS:
                start = perf_counter()
                results = backends[name].search(item["query"], 5)
                wall = (perf_counter()-start)*1000
                timing = dict(backends[name].last_latency)
                timing["wall_ms"] = wall
                runs[name].append({"repeat": repeat, "timing_ms": timing,
                                  "results": [asdict(r) for r in results]})
        for name in BACKENDS:
            first = runs[name][0]["results"]
            records[name].append({**item, "results": first,
                                  "metrics": query_metrics([r["chunk_id"] for r in first], item["expected_chunk_ids"]),
                                  "runs": runs[name],
                                  "ranking_consistent": all([r["chunk_id"] for r in run["results"]] ==
                                                           [r["chunk_id"] for r in first] for run in runs[name])})
        print(f'{item["split"]} {item["id"]}: dense / bm25 / hybrid complete', flush=True)
    output = {}
    for name in BACKENDS:
        rows = records[name]
        output[name] = {"queries": rows, "overall": summarize(rows),
                        "categories": {cat: summarize([r for r in rows if r["category"] == cat])
                                       for cat in sorted(RETRIEVAL_CATEGORIES)},
                        "latency_ms": distributions([run["timing_ms"]["wall_ms"] for r in rows for run in r["runs"]]),
                        "score_kind": rows[0]["results"][0]["score_kind"],
                        "no_answer_scores": {
                            "top1": distributions([r["results"][0]["score"] for r in rows if not r["answerable"]]),
                            "top5": distributions([x["score"] for r in rows if not r["answerable"] for x in r["results"]])},
                        "warmup": warmup[name]}
    return output

def bad_cases(outputs):
    by_method = {name: {r["id"]: r for r in outputs[name]["queries"]} for name in BACKENDS}
    groups = {k: [] for k in ("A_bm25_correct_dense_wrong", "B_dense_correct_bm25_wrong",
                              "C_hybrid_correct_both_wrong", "D_hybrid_worse_than_best_single",
                              "E_multi_evidence_coverage_failure", "F_entity_or_hard_negative_confusion")}
    for ident, q in by_method["dense"].items():
        if not q["answerable"]:
            continue
        rows = {name: by_method[name][ident] for name in BACKENDS}
        recall = {name: row["metrics"]["Recall@3"] for name, row in rows.items()}
        complete = {name: value == 1 for name, value in recall.items()}
        flags = []
        if complete["bm25"] and not complete["dense"]: flags.append("A_bm25_correct_dense_wrong")
        if complete["dense"] and not complete["bm25"]: flags.append("B_dense_correct_bm25_wrong")
        if complete["hybrid"] and not complete["dense"] and not complete["bm25"]: flags.append("C_hybrid_correct_both_wrong")
        if recall["hybrid"] < max(recall["dense"], recall["bm25"]): flags.append("D_hybrid_worse_than_best_single")
        if q["category"] == "multi_evidence" and any(value < 1 for value in recall.values()):
            flags.append("E_multi_evidence_coverage_failure")
        negative = set(q.get("hard_negative_chunk_ids", []))
        confused = {name: sorted(negative & {r["chunk_id"] for r in row["results"][:3]}) for name, row in rows.items()}
        if q["category"] in {"entity_ambiguity", "hard_negative"} and (
            any(row["metrics"]["HitRate@1"] == 0 for row in rows.values()) or any(confused.values())):
            flags.append("F_entity_or_hard_negative_confusion")
        candidate = {"id": ident, "query": q["query"], "category": q["category"],
                     "expected_chunk_ids": q["expected_chunk_ids"], "recall_at_3": recall,
                     "annotated_negatives_in_top3": confused,
                     "top5": {name: row["results"] for name, row in rows.items()},
                     "explanation_status": "candidate only; requires engineering analysis, not LLM judgement"}
        for flag in flags: groups[flag].append(candidate)
    return groups

def checked_run_dir(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT/"artifacts/v0.2/retrieval"):
        raise ValueError("run directory must be under ignored artifacts/v0.2/retrieval")
    return path

def run_dev(run_dir):
    if run_dir.exists():
        raise FileExistsError("refuse existing run directory")
    bundle, before = verify_integrity()
    if subprocess.check_output(["git", "branch", "--show-current"]).decode().strip() != "feat/v0.2-eval-hybrid":
        raise ValueError("wrong experiment branch")
    metadata = model_metadata(SETTINGS)
    run_dir.mkdir(parents=True)
    write_json(run_dir/"config.json", SETTINGS)
    write_json(run_dir/"integrity_before.json", before)
    write_json(run_dir/"provenance.json", {
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_checkpoint": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
        "dataset_manifest_sha256": digest(ROOT/"eval/v0.2/freeze_manifest.json"),
        "python": sys.version.split()[0],
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "faiss-cpu", "httpx", "tiktoken", "knowledge-base-agent", "nanobot-ai")},
        **metadata})
    backends, stats = make_backends(run_dir, SETTINGS, bundle, True)
    write_json(run_dir/"index_stats.json", stats)
    outputs = evaluate(backends, [q for q in bundle["retrieval"]["items"] if q["split"] == "dev"],
                       SETTINGS["dev_latency_repeats"])
    for name in BACKENDS: write_json(run_dir/"dev"/f"{name}.json", outputs[name])
    write_json(run_dir/"dev/comparison.json", {"bad_case_groups": bad_cases(outputs),
                                             "summary": {name: outputs[name]["overall"] for name in BACKENDS}})
    verify_integrity(before)
    from .report import dev_report
    (run_dir/"dev/REPORT.md").write_text(dev_report(outputs), encoding="utf-8", newline="\n")

def lock_config(run_dir):
    bundle, before = verify_integrity(json.loads((run_dir/"integrity_before.json").read_text()))
    outputs = [json.loads((run_dir/"dev"/f"{name}.json").read_text(encoding="utf-8")) for name in BACKENDS]
    if any(len(out["queries"]) != 36 for out in outputs):
        raise ValueError("dev run incomplete")
    settings = json.loads((run_dir/"config.json").read_text())
    if settings != SETTINGS:
        raise ValueError("dev/settings mismatch")
    # 正式test之前固化参数及代码。记录来自dev完成之后；不得覆写。
    if CONFIG_PATH.exists():
        if json.loads(CONFIG_PATH.read_text()) != settings:
            raise ValueError("existing CONFIG differs; do not change a locked experiment")
    else:
        write_json(CONFIG_PATH, settings)
    write_json(run_dir/"lock.json", {"config_sha256": digest(CONFIG_PATH),
                                    "source_hashes": source_hashes(),
                                    "dataset_manifest_sha256": digest(ROOT/"eval/v0.2/freeze_manifest.json"),
                                    "locked_at_utc": datetime.now(timezone.utc).isoformat(),
                                    "dev_completed": True})
    print("CONFIG locked:", digest(CONFIG_PATH), flush=True)

def run_test(run_dir):
    if (run_dir/"test").exists():
        raise FileExistsError("first official test results already exist; do not overwrite")
    lock = json.loads((run_dir/"lock.json").read_text())
    settings = json.loads(CONFIG_PATH.read_text())
    if (digest(CONFIG_PATH) != lock["config_sha256"] or settings != SETTINGS
        or source_hashes() != lock["source_hashes"]
        or digest(ROOT/"eval/v0.2/freeze_manifest.json") != lock["dataset_manifest_sha256"]):
        raise ValueError("config/source/dataset changed since preregistration")
    before = json.loads((run_dir/"integrity_before.json").read_text())
    bundle, _ = verify_integrity(before)
    if model_metadata(settings)["embedding_model"] != json.loads((run_dir/"provenance.json").read_text())["embedding_model"]:
        raise ValueError("embedding model changed")
    # 一旦正式test开始就写attempt marker；失败也不允许自动重跑覆盖。
    write_json(run_dir/"test/attempt.json", {"started_at_utc": datetime.now(timezone.utc).isoformat(), "lock": lock})
    backends, stats = make_backends(run_dir, settings, bundle, False)
    outputs = evaluate(backends, [q for q in bundle["retrieval"]["items"] if q["split"] == "test"],
                       settings["test_latency_repeats"])
    for name in BACKENDS: write_json(run_dir/"test"/f"{name}.json", outputs[name])
    comparison = {"config_sha256": lock["config_sha256"], "bad_case_groups": bad_cases(outputs),
                  "summary": {name: outputs[name]["overall"] for name in BACKENDS},
                  "categories": {name: outputs[name]["categories"] for name in BACKENDS}}
    write_json(run_dir/"test/comparison.json", comparison)
    write_json(run_dir/"latency_raw.json", {name: {"warmup": outputs[name]["warmup"],
                        "runs": [{"id": q["id"], "query": q["query"], "repeat": r["repeat"], **r["timing_ms"]}
                                 for q in outputs[name]["queries"] for r in q["runs"]]} for name in BACKENDS})
    verify_integrity(before)
    write_json(run_dir/"integrity_after.json", protected_hashes())
    from .report import test_report
    report = test_report(outputs, comparison, json.loads((run_dir/"provenance.json").read_text()), stats, run_dir)
    (run_dir/"test/REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps(comparison["summary"], ensure_ascii=False, indent=2), flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["dev", "lock", "test"], required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    run_dir = checked_run_dir(args.run_dir)
    try:
        {"dev": run_dev, "lock": lock_config, "test": run_test}[args.stage](run_dir)
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        if run_dir.exists() and not (run_dir/"failure.json").exists():
            write_json(run_dir/"failure.json", {"stage": args.stage, "type": type(exc).__name__,
                                               "message": str(exc), "traceback": traceback.format_exc()})
        raise

if __name__ == "__main__":
    main()
