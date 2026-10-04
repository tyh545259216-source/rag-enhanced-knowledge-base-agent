# 只执行真实检索并记录结果，不调用 Qwen，不使用阈值过滤。
import argparse,json
from pathlib import Path
from dataclasses import asdict
from datetime import datetime
from knowledge_base_agent.rag.adapter import RAGAdapter
from knowledge_base_agent.rag.retriever import Retriever
from knowledge_base_agent.rag.config import load_config

parser=argparse.ArgumentParser();parser.add_argument("--config",default="config.yaml")
args=parser.parse_args();config_path=Path(args.config).resolve();root=config_path.parent
adapter=RAGAdapter(load_config(config_path))
assert adapter.load(), "Run ingestion first"
retriever=Retriever(adapter);records=[]
for item in json.loads((root/"eval/golden_questions.json").read_text(encoding="utf-8")):
    results=retriever.search(item["query"],3)
    record={"query":item["query"],"expected_sources":item["expected_sources"],
            "results":[dict(rank=i,**asdict(result)) for i,result in enumerate(results,1)],
            "latency":adapter.last_latency}
    records.append(record)
    print(json.dumps(record,ensure_ascii=False,indent=2),flush=True)
report={"timestamp":datetime.now().astimezone().isoformat(),"stats":adapter.store.get_index_stats(),"queries":records,
        "warning":"Top-K does not imply answer exists; no similarity threshold used."}
(root/"eval/search_results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
