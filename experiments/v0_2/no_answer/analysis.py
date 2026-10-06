"""只分析已保存Dense分数。no-answer是positive；不调用Embedding或LLM。"""
import hashlib
import json
import math
import statistics
from fractions import Fraction

RULE = {
    "version": "dense-top1-threshold-1",
    "positive_class": "no_answer",
    "prediction": "top1 < threshold => no_answer; equality => answerable",
    "thresholds": [i / 100 for i in range(50, 96)],
    "selection": ["maximize no_answer F1", "minimize answerable false rejection rate", "maximize no_answer precision", "smallest threshold"],
    "last_tie_reason": "相同指标下选最低网格阈值；更保守地拒绝有答案问题，不按test挑选。",
    "undefined_precision_recall_f1": "zero; counts always reported",
    "quantiles": "linear interpolation at (n-1)*p",
    "score_source": "first official Phase2 results only; not later timing repeats",
    "margin": "top1-top2; descriptive only, never used in predictions",
}

def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def extract_scores(payload, golden, split):
    """按split核对完整ID、标签和首轮排名；missing field直接报错，不补跑。"""
    if split not in {"dev", "test"}:
        raise ValueError("invalid split")
    expected = {g["id"]: g for g in golden if g["split"] == split}
    records = payload["queries"]
    if len({c["id"] for c in records}) != len(records) or {c["id"] for c in records} != set(expected):
        raise ValueError("duplicate/missing/unexpected query IDs")
    output = []
    for c in records:
        g = expected[c["id"]]
        for key in ["query", "split", "category", "answerable", "expected_chunk_ids"]:
            if c[key] != g[key]:
                raise ValueError("frozen label/query mismatch: " + key)
        if type(c["answerable"]) is not bool:
            raise ValueError("answerable must be boolean")
        results = c["results"]
        if len(results) < 3 or len({t["chunk_id"] for t in results}) != len(results):
            raise ValueError("at least three unique ranked results required")
        scores = [t["score"] for t in results]
        if any(type(v) not in [int, float] or not math.isfinite(v) or not -1.00001 <= v <= 1.00001 for v in scores):
            raise ValueError("invalid normalized Dense score")
        if any(t["rank"] != rank for rank, t in enumerate(results, 1)) or scores != sorted(scores, reverse=True):
            raise ValueError("invalid score/rank ordering")
        if any(t["score_kind"] != "cosine_inner_product" for t in results):
            raise ValueError("only Dense cosine scores permitted")
        # 已保存的results必须确实对应repeat=1，不混用其他timing重复。
        if c["runs"][0]["repeat"] != 1 or c["runs"][0]["results"] != results:
            raise ValueError("not first official ranking")
        ranks = {t["chunk_id"]: t["rank"] for t in results}
        output.append({"id": c["id"], "query": c["query"], "split": split,
                       "category": c["category"], "answerable": c["answerable"],
                       "top1": scores[0], "top2": scores[1], "top3_scores": scores[:3],
                       "margin": scores[0] - scores[1],
                       "expected_chunk_ids": list(g["expected_chunk_ids"]),
                       "relevant_chunk_ranks_in_saved_top5": {i: ranks.get(i) for i in g["expected_chunk_ids"]},
                       "top5": [{k: t[k] for k in ["rank", "chunk_id", "score"]} for t in results]})
    return output

def distribution(values):
    if not values:
        raise ValueError("nonempty distribution required")
    xs = sorted(values)
    if any(not math.isfinite(x) for x in xs):
        raise ValueError("nonfinite value")
    def q(p):
        position = (len(xs) - 1) * p
        lo, hi = math.floor(position), math.ceil(position)
        return xs[lo] + (xs[hi] - xs[lo]) * (position - lo)
    return {"count": len(xs), "min": xs[0], "max": xs[-1], "mean": statistics.mean(xs),
            "median": statistics.median(xs), **{f"p{p}": q(p / 100) for p in [10, 25, 75, 90]}}

def describe_dev(rows):
    if not rows or any(c["split"] != "dev" for c in rows):
        raise ValueError("distribution/overlap selection analysis is dev-only")
    ans = [c for c in rows if c["answerable"]]
    no = [c for c in rows if not c["answerable"]]
    ad, nd = distribution([c["top1"] for c in ans]), distribution([c["top1"] for c in no])
    overlap = [max(ad["min"], nd["min"]), min(ad["max"], nd["max"])]
    na_ids = [c["id"] for c in no if ad["min"] <= c["top1"] <= ad["max"]]
    an_ids = [c["id"] for c in ans if nd["min"] <= c["top1"] <= nd["max"]]
    return {"top1": {"answerable": ad, "no_answer": nd},
            "margin": {"answerable": distribution([c["margin"] for c in ans]), "no_answer": distribution([c["margin"] for c in no])},
            "overlap": {"answerable_min": ad["min"], "no_answer_max": nd["max"],
                        "interval": overlap if overlap[0] <= overlap[1] else None,
                        "no_answer_in_answerable_range": {"count": len(na_ids), "total": len(no), "ids": na_ids},
                        "answerable_in_no_answer_range": {"count": len(an_ids), "total": len(ans), "ids": an_ids}}}

def metrics(rows, threshold):
    if not rows or type(threshold) not in [int, float] or not math.isfinite(threshold):
        raise ValueError("nonempty rows and finite threshold required")
    tp = fp = fn = tn = 0
    decisions = []
    for c in rows:
        if type(c["answerable"]) is not bool or not math.isfinite(c["top1"]):
            raise ValueError("invalid score/label")
        positive = not c["answerable"]
        predicted = c["top1"] < threshold
        if positive and predicted: tp += 1
        elif positive: fn += 1
        elif predicted: fp += 1
        else: tn += 1
        decisions.append({"id": c["id"], "answerable": c["answerable"], "top1": c["top1"], "predicted_no_answer": predicted})
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0
    return {"threshold": threshold, "positive_class": "no_answer", "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "no_answer_precision": precision, "no_answer_recall": recall, "no_answer_f1": f1,
            "answerable_false_rejection_rate": fp / (fp + tn) if fp + tn else 0,
            "accuracy": (tp + tn) / len(rows), "answerable_count": fp + tn, "no_answer_count": tp + fn,
            "false_rejection_ids": [c["id"] for c in decisions if c["answerable"] and c["predicted_no_answer"]],
            "missed_no_answer_ids": [c["id"] for c in decisions if not c["answerable"] and not c["predicted_no_answer"]],
            "decisions": decisions}

def selection_key(m):
    """用exact fractions排序，避免float误差改变预注册tie-break。"""
    tp, fp, fn, tn = (m[k] for k in ["TP", "FP", "FN", "TN"])
    ratio = lambda n, d: Fraction(n, d) if d else Fraction(0)
    return (ratio(2 * tp, 2 * tp + fp + fn), -ratio(fp, fp + tn), ratio(tp, tp + fp), -Fraction(str(m["threshold"])))

def scan_dev(rows):
    if not rows or any(c["split"] != "dev" for c in rows):
        raise ValueError("threshold selection cannot read test rows")
    scan = [metrics(rows, t) for t in RULE["thresholds"]]
    chosen = max(scan, key=selection_key)
    return scan, chosen

def verify_config(config):
    body = dict(config)
    digest = body.pop("config_hash")
    if canonical(body) != digest or config["selection_rule"] != RULE:
        raise ValueError("frozen threshold config hash/rule changed")
    if config["selection_split"] != "dev" or config["selected_threshold"] not in RULE["thresholds"]:
        raise ValueError("invalid selected threshold provenance")
    return config
