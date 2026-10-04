from time import perf_counter
from .schemas import Document, Chunk, SearchResult
from ..vendor.rag_core.extractor import extract_documents
from ..vendor.rag_core.chunker import chunk_fixed
from ..vendor.rag_core.faiss_store import FaissStore
from ..vendor.ollama_embeddings import embed_texts, embed_query

class RAGAdapter:
    def __init__(self, config):
        self.config = config
        self.store = FaissStore(config.store_dir, config.embedding_model)
        self.last_latency = {}

    def _args(self):
        return dict(model=self.config.embedding_model, base_url=self.config.base_url, timeout=self.config.timeout)

    def ingest(self):
        pages = extract_documents(str(self.config.data_dir))
        documents = [Document(p["text"], p["source_file"], p["page"]) for p in pages]
        raw = chunk_fixed([dict(text=d.text, source_file=d.source, page=d.page) for d in documents],
                          {"chunking": {"fixed": {"chunk_size": self.config.chunk_size, "overlap": self.config.overlap}}})
        if not raw:
            raise ValueError("No nonempty chunks")
        vectors = embed_texts([c["text"] for c in raw], **self._args())
        self.store.build_index(vectors, raw)
        return [Chunk(c["text"], c["source_file"], c["chunk_id"], c["chunk_index"], c["page"]) for c in raw]

    def load(self):
        return self.store.load_index()

    def search(self, query, top_k):
        start = perf_counter()
        vector = embed_query(query, **self._args())
        embedded = perf_counter()
        raw = self.store.search(vector, top_k)
        searched = perf_counter()
        results = [SearchResult(c["text"], c["source_file"], c["chunk_id"], c["score"], c.get("page")) for c in raw]
        self.last_latency = {"embedding_ms": (embedded-start)*1000, "faiss_ms": (searched-embedded)*1000,
                             "total_ms": (perf_counter()-start)*1000}
        return results
