"""指标只计answerable题；no-answer仍完整保留排名和分数。"""
from statistics import mean, median
import numpy as np
from .schema import validate_search

def query_metrics(ids, relevant, ks=(1, 3, 5)):
    relevant = set(relevant)
    if not relevant:
        return None
    values = {}
    for k in ks:
        validate_search("metric", k)
        retrieved = ids[:k]
        hits = len(set(retrieved) & relevant)
        rr = next((1/r for r, ident in enumerate(retrieved, 1) if ident in relevant), 0.0)
        values[f"HitRate@{k}"] = float(hits > 0)
        values[f"Recall@{k}"] = hits/len(relevant)
        if k in (3, 5):
            values[f"MRR@{k}"] = rr
    return values

def summarize(records):
    valid = [r for r in records if r["answerable"]]
    metrics = {key: mean(r["metrics"][key] for r in valid) for key in valid[0]["metrics"]} if valid else None
    hit_counts = {f"HitRate@{k}": sum(r["metrics"][f"HitRate@{k}"] for r in valid)
                  for k in (1, 3, 5)}
    return {"answerable_count": len(valid), "no_answer_count": len(records)-len(valid),
            "metrics": metrics, "hit_counts": hit_counts}

def distributions(values):
    if not values:
        return None
    return {"n": len(values), "mean": mean(values), "median": median(values),
            "p95": float(np.quantile(values, .95)), "min": min(values), "max": max(values)}
