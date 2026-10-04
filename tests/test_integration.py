from pathlib import Path
import numpy as np
import pytest
from knowledge_base_agent.vendor.ollama_embeddings import embed_texts, embed_query
from knowledge_base_agent.rag.adapter import RAGAdapter
from knowledge_base_agent.rag.retriever import Retriever
from knowledge_base_agent.rag.config import RAGConfig

pytestmark=pytest.mark.integration


def test_real_embedding():
    vectors=embed_texts(["项目 Aurora 的负责人是林澈。","服务器 SABLE-17 保存验收日志。"])
    query=embed_query("项目 Aurora 的负责人是林澈。")
    assert vectors.shape[0]==2 and vectors.shape[1]>0 and query.shape==(1,vectors.shape[1])
    assert np.isfinite(vectors).all() and np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-5)
    assert np.allclose(query[0],vectors[0],atol=1e-5)


def test_real_retriever_reload(tmp_path):
    data=tmp_path/"data";data.mkdir()
    (data/"aurora.txt").write_text("项目 Aurora 的负责人是林澈，预算为 128000 元。",encoding="utf-8")
    cfg=RAGConfig(data,tmp_path/"store","nomic-embed-text","http://localhost:11434",160,24)
    first=RAGAdapter(cfg);first.ingest()
    second=RAGAdapter(cfg);assert second.load()
    a=Retriever(first).search("Aurora 负责人",3);b=Retriever(second).search("Aurora 负责人",3)
    assert a==b and len(a)==1 and a[0].source=="aurora.txt" and a[0].page is None
    assert a[0].chunk_id=="aurora.txt:ptxt:000" and "林澈" in a[0].text
