import argparse
import json
from .rag.config import load_config
from .rag.adapter import RAGAdapter


def main():
    parser=argparse.ArgumentParser(description="PDF/TXT 入库，不调用生成模型")
    parser.add_argument("--config",default="config.yaml")
    args=parser.parse_args()
    adapter=RAGAdapter(load_config(args.config));adapter.ingest()
    print(json.dumps(adapter.store.get_index_stats(),ensure_ascii=False,indent=2))

if __name__=="__main__":main()
