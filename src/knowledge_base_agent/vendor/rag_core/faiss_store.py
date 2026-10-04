"""改编来源：https://github.com/tajwarchy/rag-from-scratch
原始文件：core/faiss_store.py
commit：4c4e039177ce2a7ac475339cff7a1187a6fd68bf
MIT License，完整版权声明见 licenses/。
修改：保留 build/load/search 主体；IP；实例状态；显式路径；Unicode IO；数量/维度/哈希校验；index_info。
"""

import hashlib
import json
from pathlib import Path
import faiss
import numpy as np


class FaissStore:
    def __init__(self, store_dir: Path, embedding_model: str):
        self.store_dir = Path(store_dir)
        self.embedding_model = embedding_model
        self._index = None
        self._chunks = []

    def _vectors(self, values, query=False):
        arr = np.asarray(values, dtype="float32")
        if arr.ndim != 2 or arr.shape[1] == 0 or not np.isfinite(arr).all():
            raise ValueError("Finite 2D vectors required")
        if query and (arr.shape[0] != 1 or arr.shape[1] != self._index.d):
            raise ValueError("Query dimension/shape mismatch")
        if not np.allclose(np.linalg.norm(arr, axis=1), 1, atol=1e-5):
            raise ValueError("L2 normalized vectors required")
        return np.ascontiguousarray(arr)

    @staticmethod
    def _metadata(chunks):
        ids = [c["chunk_id"] for c in chunks]
        if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
            raise ValueError("Unique nonempty string chunk IDs required")
        for c in chunks:
            if not isinstance(c.get("text"), str) or not c["text"].strip() or not isinstance(c.get("source_file"), str):
                raise ValueError("Invalid text/source metadata")

    def build_index(self, embeddings, chunks):
        embeddings = self._vectors(embeddings)
        if not chunks or len(chunks) != len(embeddings):
            raise ValueError("Nonempty vector/metadata count must match")
        self._metadata(chunks)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        index_path = self.store_dir / "index.faiss"
        with index_path.open("wb") as handle:
            faiss.write_index(index, faiss.PyCallbackIOWriter(handle.write))
        metadata = json.dumps(chunks, ensure_ascii=False, indent=2).encode("utf-8")
        (self.store_dir / "metadata.json").write_bytes(metadata)
        info = {"embedding_model": self.embedding_model, "vector_dimension": dim,
                "chunk_count": len(chunks), "index_type": "IndexFlatIP", "normalized": True,
                "metadata_sha256": hashlib.sha256(metadata).hexdigest(),
                "index_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest()}
        (self.store_dir / "index_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
        self._index, self._chunks = index, chunks

    def load_index(self):
        paths = [self.store_dir / n for n in ("index.faiss", "metadata.json", "index_info.json")]
        if not any(p.exists() for p in paths):
            self._index, self._chunks = None, []
            return False
        if not all(p.exists() for p in paths):
            raise ValueError("Incomplete persisted index")
        info = json.loads(paths[2].read_text(encoding="utf-8"))
        metadata = paths[1].read_bytes()
        if info["metadata_sha256"] != hashlib.sha256(metadata).hexdigest() or info["index_sha256"] != hashlib.sha256(paths[0].read_bytes()).hexdigest():
            raise ValueError("Persistence integrity mismatch")
        with paths[0].open("rb") as handle:
            index = faiss.read_index(faiss.PyCallbackIOReader(handle.read))
        chunks = json.loads(metadata)
        self._metadata(chunks)
        if (info["embedding_model"] != self.embedding_model or info["normalized"] is not True
            or info["index_type"] != "IndexFlatIP" or not isinstance(index, faiss.IndexFlatIP)
            or index.d != info["vector_dimension"] or index.ntotal != info["chunk_count"]
            or index.ntotal != len(chunks)):
            raise ValueError("Model/dimension/count/type mismatch")
        self._index, self._chunks = index, chunks
        return True

    def search(self, query_vec, top_k):
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be positive integer")
        if self._index is None:
            raise RuntimeError("No FAISS index loaded")
        query_vec = self._vectors(query_vec, query=True)
        if self._index.ntotal == 0:
            return []
        scores, indices = self._index.search(query_vec, min(top_k, self._index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk = dict(self._chunks[idx])
            chunk["score"] = float(score)
            results.append(chunk)
        return results

    def get_index_stats(self):
        return {"index_type": "IndexFlatIP", "ntotal": self._index.ntotal if self._index is not None else 0,
                "vector_dimension": self._index.d if self._index is not None else None,
                "metadata_count": len(self._chunks)}
