"""Dense复用现有RAGAdapter/Retriever；Hybrid是实验封装，不改默认行为。"""
from pathlib import Path
from time import perf_counter
from knowledge_base_agent.rag.adapter import RAGAdapter
from knowledge_base_agent.rag.config import RAGConfig
from knowledge_base_agent.rag.retriever import Retriever
from .schema import RankedResult, reciprocal_rank_fusion, validate_search

def isolated_store(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    if not path.is_relative_to(root/"artifacts/v0.2/retrieval"):
        raise ValueError("V0.2 index must stay under ignored artifacts/v0.2/retrieval")
    return path

class DenseBackend:
    def __init__(self, root, store_dir, settings, dataset_config):
        root = Path(root).resolve()
        store_dir = isolated_store(root, store_dir)
        data_dir = (root/dataset_config["corpus_dir"]).resolve()
        if not data_dir.is_relative_to(root/"eval/v0.2"):
            raise ValueError("V0.2 corpus must be isolated")
        cfg = RAGConfig(data_dir, store_dir, settings["embedding_model"],
                        settings["ollama_url"], dataset_config["chunk_size"],
                        dataset_config["overlap"], settings["timeout_seconds"])
        self.adapter = RAGAdapter(cfg)
        self.retriever = Retriever(self.adapter)
        self.last_latency = {}

    def ingest(self, expected_chunks):
        chunks = self.adapter.ingest()
        actual = [(c.chunk_id, c.source, c.text, c.page) for c in chunks]
        expected = [(c["chunk_id"], c["source"], c["text"], c.get("page")) for c in expected_chunks]
        if actual != expected:
            raise ValueError("ingested chunks differ from frozen corpus")
        return self.adapter.store.get_index_stats()

    def load(self):
        if not self.adapter.load():
            raise FileNotFoundError("V0.2 index missing")
        return self.adapter.store.get_index_stats()

    def search(self, query, top_k=3):
        items = self.retriever.search(query, top_k)
        results = [RankedResult(c.chunk_id, rank, c.score, c.source, c.text,
                                c.page, "cosine_inner_product") for rank, c in enumerate(items, 1)]
        self.last_latency = dict(self.adapter.last_latency)
        return results

class HybridBackend:
    def __init__(self, dense, bm25, candidate_pool=20, rrf_k=60):
        if type(candidate_pool) is not int or candidate_pool <= 0 or type(rrf_k) is not int or rrf_k <= 0:
            raise ValueError("positive candidate pool/RRF k required")
        self.dense, self.bm25 = dense, bm25
        self.candidate_pool, self.rrf_k = candidate_pool, rrf_k
        self.last_latency = {}

    def search(self, query, top_k=3):
        validate_search(query, top_k)
        if top_k > self.candidate_pool:
            raise ValueError("top_k exceeds locked candidate pool")
        start = perf_counter()
        dense = self.dense.search(query, self.candidate_pool)
        dense_timing = dict(self.dense.last_latency)
        lexical = self.bm25.search(query, self.candidate_pool)
        fusion_start = perf_counter()
        results = reciprocal_rank_fusion([dense, lexical], self.rrf_k)[:top_k]
        self.last_latency = {**dense_timing, **self.bm25.last_latency,
                             "rrf_ms": (perf_counter()-fusion_start)*1000,
                             "hybrid_ms": (perf_counter()-start)*1000}
        return results
