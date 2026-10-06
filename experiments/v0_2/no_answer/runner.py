"""阶段化离线分析：dev锁定后才解析test；不覆盖、不重跑检索。"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from .analysis import RULE, canonical, extract_scores, describe_dev, scan_dev, metrics, verify_config
from experiments.v0_2.retrieval.runner import verify_integrity, digest

ROOT = Path(__file__).resolve().parents[3]
PHASE2 = ROOT / "artifacts/v0.2/retrieval/phase2_first_20261005"
CONFIG = ROOT / "experiments/v0_2/no_answer/THRESHOLD_CONFIG.json"

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_once(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")

def source_hashes():
    files = list((ROOT / "experiments/v0_2/no_answer").glob("*.py"))
    files += [ROOT / "scripts/v0_2/analyze_no_answer.py", ROOT / "tests/v0_2/test_no_answer.py"]
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(files)}

def golden():
    return read(ROOT / "eval/v0.2/retrieval_golden.json")["items"]

def verify(run_dir):
    lock = read(run_dir / "lock.json")
    cfg = verify_config(read(CONFIG))
    if digest(CONFIG) != lock["threshold_config_file_hash"] or source_hashes() != cfg["source_hashes"]:
        raise ValueError("config/source changed after dev lock")
    verify_integrity(lock["protected_files"])
    for label, source in [("phase2", PHASE2), ("routing", ROOT / "artifacts/v0.2/routing/phase3_first_20261005"), ("ablation", ROOT / "artifacts/v0.2/ablation/phase3b_first_20261005")]:
        for rel, h in lock["historical_files"][label].items():
            if digest(source / rel) != h:
                raise ValueError("historical artifact changed: " + label + "/" + rel)
    return cfg

def run_dev(run_dir):
    if run_dir.exists():
        raise FileExistsError("new isolated run directory required")
    _, protected = verify_integrity()
    payload = read(PHASE2 / "dev/dense.json")  # 不解析test/dense.json。
    rows = extract_scores(payload, golden(), "dev")
    if len(rows) != 36 or sum(c["answerable"] for c in rows) != 30:
        raise ValueError("expected frozen dev 30 answerable + 6 no-answer")
    description = describe_dev(rows)
    scan, selected = scan_dev(rows)
    config = {"version": "phase4a-threshold-first", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "selection_split": "dev", "selection_rule": RULE,
              "selected_threshold": selected["threshold"], "dev_metrics": selected,
              "dense_config": read(ROOT / "experiments/v0_2/retrieval/CONFIG.json"),
              "dense_config_hash": digest(ROOT / "experiments/v0_2/retrieval/CONFIG.json"),
              "dataset_hash": digest(ROOT / "eval/v0.2/freeze_manifest.json"),
              "retrieval_dataset_hash": digest(ROOT / "eval/v0.2/retrieval_golden.json"),
              "dev_source_hash": digest(PHASE2 / "dev/dense.json"), "source_hashes": source_hashes()}
    config["config_hash"] = canonical(config)
    if CONFIG.exists():
        prior = verify_config(read(CONFIG))
        for k in ["selection_split", "selection_rule", "selected_threshold", "dev_metrics", "dense_config_hash", "dataset_hash", "retrieval_dataset_hash", "dev_source_hash", "source_hashes"]:
            if prior[k] != config[k]:
                raise ValueError("new run differs from frozen config: " + k)
        config = prior
    else:
        write_once(CONFIG, config)
    run_dir.mkdir(parents=True)
    historical = {}
    for label, source in [("phase2", PHASE2), ("routing", ROOT / "artifacts/v0.2/routing/phase3_first_20261005"), ("ablation", ROOT / "artifacts/v0.2/ablation/phase3b_first_20261005")]:
        historical[label] = {p.relative_to(source).as_posix(): digest(p) for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    write_once(run_dir / "lock.json", {"locked_at_utc": datetime.now(timezone.utc).isoformat(), "threshold_config_file_hash": digest(CONFIG), "protected_files": protected, "historical_files": historical,
                                       "access_protocol": "dev/dense parsed; test bytes only hashed before config freeze; no test scores used in selection"})
    write_once(run_dir / "dev_scores.json", rows)
    write_once(run_dir / "dev_distribution.json", description)
    write_once(run_dir / "dev_scan.json", scan)
    write_once(run_dir / "selected_config.json", config)
    verify(run_dir)
    print(json.dumps({"dev": description, "selected_threshold": selected["threshold"], "dev_metrics": {k: v for k, v in selected.items() if k != "decisions"}, "config_hash": config["config_hash"]}, ensure_ascii=False))

def run_test(run_dir):
    cfg = verify(run_dir)
    # attempt排他创建在读取test分数之前；即便失败也保留首次尝试。
    write_once(run_dir / "test_attempt.json", {"started_at_utc": datetime.now(timezone.utc).isoformat(), "config_hash": cfg["config_hash"], "threshold": cfg["selected_threshold"], "model_or_retrieval_rerun": False})
    rows = extract_scores(read(PHASE2 / "test/dense.json"), golden(), "test")
    dev_ids = {c["id"] for c in read(run_dir / "dev_scores.json")}
    if dev_ids & {c["id"] for c in rows} or len(rows) != 24 or sum(c["answerable"] for c in rows) != 20:
        raise ValueError("frozen test split invalid")
    result = metrics(rows, cfg["selected_threshold"])
    write_once(run_dir / "test_scores.json", rows)
    write_once(run_dir / "test_result.json", result)
    verify(run_dir)
    print(json.dumps({k: v for k, v in result.items() if k != "decisions"}, ensure_ascii=False))

def report(run_dir, decision, reason, publish=False):
    cfg = verify(run_dir)
    if decision not in {"A", "B", "C"} or not reason:
        raise ValueError("explicit engineering decision/reason required; do not change threshold")
    d, test = read(run_dir / "dev_distribution.json"), read(run_dir / "test_result.json")
    attempt = read(run_dir / "test_attempt.json")
    if attempt["config_hash"] != cfg["config_hash"] or test["threshold"] != cfg["selected_threshold"]:
        raise ValueError("test did not use selected frozen threshold")
    limitations = ["synthetic corpus; 40-chunk controlled benchmark", "dev no-answer only 6; test no-answer only 4", "single nomic-embed-text embedding model, normalized FAISS IndexFlatIP, Dense Top1 score only", "manually designed corpus/questions; no statistical significance claim", "threshold may not generalize to other corpora/models", "历史test最高no-answer分数已公开，不宣称此前完全blind；本轮只用dev确定规则与候选，没有用test调参", "predicted no-answer is a score-based proxy for insufficient evidence, not proof of corpus answer absence", "Top5以外的relevant rank为unknown，不代表不存在或获得全库排名"]
    data = {"experiment": "phase4a-threshold-first", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_hash": cfg["dataset_hash"], "retrieval_dataset_hash": cfg["retrieval_dataset_hash"],
            "dense_config": cfg["dense_config"], "dense_config_hash": cfg["dense_config_hash"],
            "dev_source_hash": cfg["dev_source_hash"], "test_source_hash": digest(PHASE2 / "test/dense.json"),
            "selection_rule": RULE, "dev_distribution": d, "overlap": d["overlap"],
            "scan_summary": [{k: v for k, v in row.items() if k != "decisions"} for row in read(run_dir / "dev_scan.json")],
            "selected_threshold": cfg["selected_threshold"], "threshold_config_hash": cfg["config_hash"], "threshold_config_file_hash": digest(CONFIG),
            "config_locked_at": read(run_dir / "lock.json")["locked_at_utc"], "test_applied_at": attempt["started_at_utc"],
            "dev_metrics": {k: v for k, v in cfg["dev_metrics"].items() if k != "decisions"},
            "frozen_test": test, "decision": {"label": decision, "reason": reason, "default_pipeline_changed": False}, "limitations": limitations,
            "history_observation": {"test_no_answer_highest_top1": max(c["top1"] for c in read(run_dir / "test_scores.json") if not c["answerable"]), "interpretation": "High similarity does not imply answer existence in this benchmark / embedding / corpus."}}
    write_once(run_dir / "analysis_summary.json", data)
    lines = ["# V0.2 Phase 4A — No-answer / Similarity Threshold Feasibility", "", "## Protocol", "",
             "复用Phase2首次Dense dev/test JSON，不调用Embedding、FAISS search或LLM。正类no-answer；score<threshold判insufficient evidence，等于阈值判answerable。仅dev 36题（30/6）扫描；候选锁定后一次应用test 24题（20/4）。", "score越高仅表示embedding similarity，不是answer probability，也不能证明是否存在完整答案。margin仅描述，不参与预测。", "", "## Dev distributions", ""]
    for label, stats in d["top1"].items():
        lines.append("- " + label + ": " + json.dumps(stats))
    for label, stats in d["margin"].items():
        lines.append("- top1-top2 " + label + ": " + json.dumps(stats))
    lines += ["", "## Overlap", "", json.dumps(d["overlap"], ensure_ascii=False), "", "## Candidate selection", "",
              "预注册网格0.50至0.95、步长0.01共46个候选；用exact Fraction比较F1/FRR/precision，最终同指标选择最低阈值以减少拒绝风险。任何test分数都不参与scan/选择。",
              f"Selected threshold: {cfg['selected_threshold']}; config hash: `{cfg['config_hash']}`.",
              "Dev metrics: " + json.dumps(data["dev_metrics"], ensure_ascii=False), "", "## Frozen test", "",
              json.dumps({k: v for k, v in test.items() if k != "decisions"}, ensure_ascii=False),
              f"No-answer detected {test['TP']}/{test['no_answer_count']}; answerable wrongly rejected {test['FP']}/{test['answerable_count']}.",
              "", "## Decision", "", decision + ": " + reason,
              "在当前benchmark：fixed similarity threshold may not reliably separate answerable and no-answer queries。这里的局限由有限样本的重叠/误拒证据支持，不是普遍理论定理。" if d["overlap"]["interval"] else "本次dev min/max无重叠仍不能证明跨语料适用。",
              "未将threshold接入Retriever、Tool、Router或默认pipeline。没有test后调参或特殊query规则。", "", "## Historical comparison", "",
              f"复用首次test中最高no-answer Top1={data['history_observation']['test_no_answer_highest_top1']:.6f}（历史约0.8961）。它表示相似内部主题，不证明所问属性有答案。V0.1无答案查询仍返回Top-K的观察与此一致；不混合两语料的分数作校准。", "", "## Limitations", ""]
    lines += ["- " + x for x in limitations]
    lines += ["", "## Reproduction", "", "```powershell", "python scripts/v0_2/analyze_no_answer.py --stage dev --run-dir artifacts/v0.2/no_answer/<new-run>", "python scripts/v0_2/analyze_no_answer.py --stage test --run-dir artifacts/v0.2/no_answer/<new-run>", "python scripts/v0_2/analyze_no_answer.py --stage report --run-dir artifacts/v0.2/no_answer/<new-run> --decision " + decision + " --reason 'engineering interpretation; no threshold tuning'", "```", "依赖本地保存的Phase2 raw Dense结果；缺文件/字段停止，不重跑official test。新run目录的REPORT.md和export/PHASE4_THRESHOLD.json为新本地派生输出。--publish仅首次创建两个正式docs，拒绝覆盖历史。threshold config/source hash不符就停止。", "原始manifest覆盖本轮分析输入/输出JSON与REPORT.md；排除manifest本身及其派生export，避免自引用hash。"]
    with (run_dir / "REPORT.md").open("x", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    manifest = {p.relative_to(run_dir).as_posix(): digest(p) for p in sorted(run_dir.rglob("*")) if p.is_file() and "export" not in p.parts and p.name != "raw_manifest.json"}
    write_once(run_dir / "raw_manifest.json", manifest)
    snapshot = {**data, "raw_path_label": run_dir.relative_to(ROOT).as_posix(), "raw_manifest": manifest, "raw_manifest_hash": digest(run_dir / "raw_manifest.json"), "manifest_scope": "all analysis files except manifest and derived export"}
    write_once(run_dir / "export/PHASE4_THRESHOLD.json", snapshot)
    if publish:
        write_once(ROOT / "docs/v0.2/evidence/PHASE4_THRESHOLD.json", snapshot)
        with (ROOT / "docs/v0.2/NO_ANSWER_REPORT.md").open("x", encoding="utf-8", newline="\n") as f:
            f.write((run_dir / "REPORT.md").read_text(encoding="utf-8"))
    verify(run_dir)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", required=True, choices=["dev", "test", "report"])
    p.add_argument("--run-dir", required=True)
    p.add_argument("--decision", choices=["A", "B", "C"])
    p.add_argument("--reason")
    p.add_argument("--publish", action="store_true")
    a = p.parse_args()
    path = Path(a.run_dir).resolve()
    if not path.is_relative_to(ROOT / "artifacts/v0.2/no_answer"):
        raise ValueError("isolated ignored no_answer run directory required")
    if a.stage == "dev": run_dev(path)
    elif a.stage == "test": run_test(path)
    else: report(path, a.decision, a.reason, a.publish)

if __name__ == "__main__":
    main()
