"""纯离线分析单元测试；合成score仅验证算法，不能证明真实Embedding效果。"""
import json
from copy import deepcopy
import pytest
from experiments.v0_2.no_answer.analysis import (RULE, canonical, extract_scores, distribution, describe_dev, metrics, scan_dev, selection_key, verify_config)
from experiments.v0_2.no_answer import runner

def fixture():
    gold = [{"id": "q", "query": "问句", "split": "dev", "category": "exact_keyword", "answerable": True, "expected_chunk_ids": ["b", "outside"]}]
    results = [{"rank": i + 1, "chunk_id": c, "score": score, "score_kind": "cosine_inner_product"} for i, (c, score) in enumerate(zip(["a", "b", "c"], [.9, .8, .7]))]
    row = {**gold[0], "results": results, "runs": [{"repeat": 1, "results": deepcopy(results)}]}
    return {"queries": [row]}, gold

def sample(label, score, ident="q", split="dev"):
    return {"id": ident, "split": split, "answerable": label, "top1": score, "margin": .01}

def test_extract_first_scores_margin_and_relevant_rank():
    p, g = fixture();row = extract_scores(p, g, "dev")[0]
    assert row["top3_scores"] == [.9, .8, .7]
    assert row["margin"] == pytest.approx(.1)
    assert row["relevant_chunk_ranks_in_saved_top5"] == {"b": 2, "outside": None}

@pytest.mark.parametrize("bad", ["duplicate_id", "missing_id", "wrong_label", "wrong_category", "few_scores", "duplicate_chunk", "bad_rank", "bad_order", "nan", "inf", "wrong_kind", "not_first_run"])
def test_extraction_rejects_corrupt_saved_result(bad):
    p, g = fixture();c = p["queries"][0]
    if bad == "duplicate_id": p["queries"].append(deepcopy(c))
    elif bad == "missing_id": p["queries"] = []
    elif bad == "wrong_label": c["answerable"] = False
    elif bad == "wrong_category": c["category"] = "no_answer"
    elif bad == "few_scores": c["results"] = c["results"][:2]
    elif bad == "duplicate_chunk": c["results"][1]["chunk_id"] = "a"
    elif bad == "bad_rank": c["results"][0]["rank"] = 2
    elif bad == "bad_order": c["results"][1]["score"] = .95
    elif bad in ["nan", "inf"]: c["results"][0]["score"] = float(bad)
    elif bad == "wrong_kind": c["results"][0]["score_kind"] = "bm25"
    else: c["runs"][0]["repeat"] = 2
    with pytest.raises(ValueError): extract_scores(p, g, "dev")

def test_no_answer_positive_confusion_counts():
    rows = [sample(False, .6, "tp"), sample(True, .6, "fp"), sample(False, .9, "fn"), sample(True, .9, "tn")]
    m = metrics(rows, .8)
    assert [m[k] for k in ["TP", "FP", "FN", "TN"]] == [1, 1, 1, 1]
    assert m["no_answer_precision"] == m["no_answer_recall"] == m["no_answer_f1"] == .5
    assert m["answerable_false_rejection_rate"] == .5
    assert m["false_rejection_ids"] == ["fp"] and m["missed_no_answer_ids"] == ["fn"]

@pytest.mark.parametrize("score,expected", [(.7999, True), (.8, False), (.8001, False)])
def test_strict_less_than_boundary(score, expected):
    assert metrics([sample(False, score)], .8)["decisions"][0]["predicted_no_answer"] is expected

def test_no_predicted_positive_reports_zero_precision():
    m = metrics([sample(False, .9), sample(True, .95, "a")], .5)
    assert m["no_answer_precision"] == m["no_answer_recall"] == m["no_answer_f1"] == 0
    assert m["FP"] == m["TP"] == 0

def test_distribution_quantiles_and_overlap_are_explicit():
    d = distribution([0, 1, 2, 3, 4])
    assert d["p10"] == .4 and d["p25"] == 1 and d["p75"] == 3 and d["p90"] == 3.6
    info = describe_dev([sample(True, .7, "a"), sample(True, .9, "b"), sample(False, .8, "n1"), sample(False, .85, "n2")])
    assert info["overlap"]["interval"] == [.8, .85]
    assert info["overlap"]["no_answer_in_answerable_range"]["count"] == 2
    assert info["overlap"]["answerable_in_no_answer_range"]["count"] == 0

@pytest.mark.parametrize("method", [describe_dev, scan_dev])
def test_selection_and_distribution_refuse_test_split(method):
    with pytest.raises(ValueError, match="dev|test"): method([sample(False, .7, split="test")])

def key(tp, fp, fn, tn, threshold):
    return selection_key(dict(TP=tp, FP=fp, FN=fn, TN=tn, threshold=threshold))

def test_selection_prefers_f1_before_accuracy():
    assert key(4, 5, 2, 25, .8) > key(0, 0, 6, 30, .5)

def test_selection_frr_tiebreak():
    # F1都为1/2，先选更低answerable误拒率。
    assert key(2, 1, 3, 29, .7) > key(3, 3, 3, 27, .8)

def test_selection_precision_tiebreak_key():
    # 合成计数只验证tuple优先级；同一固定数据集前两tie通常已固定precision。
    assert key(3, 2, 4, 8, .8) > key(2, 2, 2, 8, .7)

def test_selection_conservative_low_threshold_last():
    assert key(2, 1, 3, 29, .71) > key(2, 1, 3, 29, .72)

def test_deterministic_scan_and_no_test_data():
    rows = [sample(True, .9, "a"), sample(False, .7, "n")]
    scan, chosen = scan_dev(rows)
    assert len(scan) == 46 and chosen["threshold"] == .71
    assert scan_dev(list(reversed(rows)))[1]["threshold"] == chosen["threshold"]
    assert scan_dev(rows) == (scan, chosen)

def test_frozen_config_hash_and_rule():
    c = {"selection_split": "dev", "selection_rule": RULE, "selected_threshold": .8}
    c["config_hash"] = canonical(c)
    assert verify_config(c) == c
    changed = deepcopy(c);changed["selected_threshold"] = .81
    with pytest.raises(ValueError, match="hash"): verify_config(changed)

def test_config_cannot_rename_selection_split_to_test():
    c = {"selection_split": "test", "selection_rule": RULE, "selected_threshold": .8};c["config_hash"] = canonical(c)
    with pytest.raises(ValueError, match="provenance"): verify_config(c)

def test_test_attempt_written_before_test_scores_and_no_repeat(tmp_path, monkeypatch):
    root = tmp_path / "root";run = root / "artifacts/run";run.mkdir(parents=True)
    (run / "dev_scores.json").write_text("[]")
    phase2 = root / "phase2"
    cfg = {"config_hash": "fixed", "selected_threshold": .8}
    monkeypatch.setattr(runner, "verify", lambda p: cfg)
    monkeypatch.setattr(runner, "PHASE2", phase2)
    monkeypatch.setattr(runner, "golden", lambda: [])
    original = runner.read
    def checked_read(path):
        if path == phase2 / "test/dense.json":
            assert (run / "test_attempt.json").exists()
            assert original(run / "test_attempt.json")["threshold"] == .8
            return {"queries": []}
        return original(path)
    monkeypatch.setattr(runner, "read", checked_read)
    rows = [sample(i < 20, .7, str(i), "test") for i in range(24)]
    monkeypatch.setattr(runner, "extract_scores", lambda p, g, split: rows)
    runner.run_test(run)
    before = (run / "test_result.json").read_bytes()
    with pytest.raises(FileExistsError): runner.run_test(run)
    assert (run / "test_result.json").read_bytes() == before
