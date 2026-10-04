"""评估层：不修改 Retriever、资料或索引，不调用生成模型。"""
import argparse,json,hashlib,statistics,time
from pathlib import Path
from dataclasses import asdict
from datetime import datetime
import httpx
from knowledge_base_agent.rag.config import load_config
from knowledge_base_agent.rag.adapter import RAGAdapter
from knowledge_base_agent.rag.retriever import Retriever


def metrics(ids,relevant,k):
    retrieved=ids[:k]; relevant=set(relevant)
    if not relevant: return None
    hits=len(set(retrieved)&relevant)
    rr=next((1/rank for rank,c in enumerate(retrieved,1) if c in relevant),0.0)
    return {"hit_rate":float(hits>0),"recall":hits/len(relevant),"mrr":rr}


def distribution(values):
    values=sorted(values)
    def quantile(p):
        pos=(len(values)-1)*p; lo=int(pos);hi=min(lo+1,len(values)-1)
        return values[lo]+(values[hi]-values[lo])*(pos-lo)
    return {"n":len(values),"min":min(values),"max":max(values),"mean":statistics.mean(values),
            "p50":quantile(.5),"p95":quantile(.95)} if values else None


def fingerprint(root):
    files=list((root/"src").rglob("*.py"))+list((root/"data").rglob("*"))+list((root/"store").glob("*"))+[root/"config.yaml"]
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--config",default="config.yaml");parser.add_argument("--repeats",type=int,default=3)
    args=parser.parse_args()
    if args.repeats<1:raise ValueError("repeats must be positive")
    root=Path(args.config).resolve().parent; before=fingerprint(root)
    golden=json.loads((root/"eval/retrieval_golden.json").read_text(encoding="utf-8"))
    if hashlib.sha256((root/"store/index_info.json").read_bytes()).hexdigest()!=golden["index_info_sha256"]:raise ValueError("Golden dataset refers to a different index")
    metadata=json.loads((root/"store/metadata.json").read_text(encoding="utf-8"));known={c["chunk_id"] for c in metadata}
    assert len({q["id"] for q in golden["items"]})==len(golden["items"])
    for q in golden["items"]:
        assert q["answerable"]==bool(q["relevant_chunk_ids"])
        assert len(q["relevant_chunk_ids"])==len(set(q["relevant_chunk_ids"]))
        assert set(q["relevant_chunk_ids"])<=known
    cfg=load_config(args.config);adapter=RAGAdapter(cfg);assert adapter.load();retriever=Retriever(adapter)
    # 单独记录首个请求；不将它冒称为真正模型冷启动。
    start=time.perf_counter();retriever.search(golden["items"][0]["query"],5)
    warmup={**adapter.last_latency,"wall_ms":(time.perf_counter()-start)*1000}
    records=[]
    for q in golden["items"]:
        runs=[];results=None
        for _ in range(args.repeats):
            start=time.perf_counter();current=retriever.search(q["query"],5)
            runs.append({**adapter.last_latency,"wall_ms":(time.perf_counter()-start)*1000})
            if results is not None and [x.chunk_id for x in current]!=[x.chunk_id for x in results]:raise RuntimeError("Ranking changed across repetitions")
            results=current
        ids=[x.chunk_id for x in results]
        records.append({**q,"results":[dict(rank=i,**asdict(x)) for i,x in enumerate(results,1)],
                        "metrics":{str(k):metrics(ids,q["relevant_chunk_ids"],k) for k in [1,3,5]},"latency_runs":runs})
        print(q["id"],q["query"],flush=True)
    answerable=[q for q in records if q["answerable"]];neg=[q for q in records if not q["answerable"]]
    summary={str(k):{metric:statistics.mean(q["metrics"][str(k)][metric] for q in answerable) for metric in ['hit_rate','recall','mrr']} for k in [1,3,5]}
    latency={key:distribution([run[key] for q in records for run in q["latency_runs"]]) for key in warmup}
    scores={"answerable_top1":distribution([q["results"][0]["score"] for q in answerable]),
            "no_answer_top1":distribution([q["results"][0]["score"] for q in neg]),
            "no_answer_top5_all":distribution([x["score"] for q in neg for x in q["results"]])}
    bad=[]
    for q in records:
        if not q["answerable"] or q["metrics"]["1"]["hit_rate"]==0 or q["metrics"]["3"]["recall"]<1:
            bad.append({"id":q["id"],"query":q["query"],"kind":"no_answer_returns_neighbors" if not q["answerable"] else "top1_wrong" if q["metrics"]["1"]["hit_rate"]==0 else "partial_recall_at_3",
                        "missing_at_3":sorted(set(q["relevant_chunk_ids"])-{x["chunk_id"] for x in q["results"][:3]}),"top1":q["results"][0]})
    assert before==fingerprint(root),"Core/data/index changed during evaluation"
    models=httpx.get(cfg.base_url+"/api/tags",timeout=30).json()["models"]
    report={"timestamp":datetime.now().astimezone().isoformat(),"embedding_models":[{k:m.get(k) for k in ['name','digest','size']} for m in models if m['name'].startswith(cfg.embedding_model)],
            "dataset_version":golden['version'],"answerable_count":len(answerable),"no_answer_count":len(neg),"repeats":args.repeats,"summary":summary,"latency_ms":latency,"first_request_ms":warmup,"score_distributions":scores,"bad_cases":bad,"queries":records,"unchanged_fingerprints":before}
    (root/"eval/retrieval_baseline.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:report[k] for k in ['summary','latency_ms','score_distributions']},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
