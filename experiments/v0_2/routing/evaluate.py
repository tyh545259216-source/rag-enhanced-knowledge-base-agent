"""只从真实trace统计，不执行路由决策或生成模型调用。"""
from statistics import mean,median
import numpy as np
from .config import TOOL
def confusion(expected,actual):
    return "TP" if expected and actual else "FN" if expected else "FP" if actual else "TN"
def routing_metrics(cases):
    c={k:0 for k in ("TP","FP","FN","TN")}
    for row in cases:c[confusion(row["expected_use_tool"],row["actual_use_tool"])]+=1
    tp,fp,fn,tn=[c[k] for k in ("TP","FP","FN","TN")]
    precision=tp/(tp+fp) if tp+fp else 0.;recall=tp/(tp+fn) if tp+fn else 0.
    return {**c,"correct":tp+tn,"total":len(cases),"accuracy":(tp+tn)/len(cases) if cases else None,
            "precision":precision,"recall":recall,"f1":2*precision*recall/(precision+recall) if precision+recall else 0.}
def distribution(values):
    return {"n":len(values),"mean":mean(values),"median":median(values),"p95":float(np.quantile(values,.95))} if values else None
def argument_valid(call):
    a=call.get("arguments")
    return (call.get("name")==TOOL and isinstance(a,dict) and set(a)<= {"query","top_k"}
            and isinstance(a.get("query"),str) and bool(a["query"].strip())
            and type(a.get("top_k",3)) is int and 1<=a.get("top_k",3)<=10)
def summarize(cases):
    categories=sorted({c["category"] for c in cases})
    latency={}
    for name,used in (("no_tool",False),("tool",True)):
        selected=[c for c in cases if c["actual_use_tool"]==used]
        latency[name]={"e2e_ms":distribution([c["latency_ms"] for c in selected])}
        if used:
            for label,values in {
                "llm1_ms":[c["requests"][0]["latency_ms"] for c in selected if c["requests"] and c["requests"][0].get("latency_ms") is not None],
                "retrieval_tool_ms":[sum(r["latency_ms"] for r in c["tool_results"]) for c in selected if c["tool_results"]],
                "llm2_ms":[c["requests"][1]["latency_ms"] for c in selected if len(c["requests"])>1 and c["requests"][1].get("latency_ms") is not None],
            }.items():latency[name][label]=distribution(values)
    calls=[call for c in cases for call in c["tool_calls"]]
    return {"metrics":routing_metrics(cases),"categories":{cat:routing_metrics([c for c in cases if c["category"]==cat]) for cat in categories},
            "bad_case_ids":{kind:[c["id"] for c in cases if c["confusion"]==kind] for kind in ("FP","FN")},
            "argument_valid_count":sum(argument_valid(call) for call in calls),"total_calls":len(calls),
            "native_structured_calls":sum(call.get("native_structured",False) for call in calls),
            "latency":latency,"model_errors":[c["id"] for c in cases if c.get("error")],
            "request_count":sum(len(c["requests"]) for c in cases),
            "request_http_statuses":sorted({r.get("http_status") for c in cases for r in c["requests"] if r.get("http_status") is not None})}
