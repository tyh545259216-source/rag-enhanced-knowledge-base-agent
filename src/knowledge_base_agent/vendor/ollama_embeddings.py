"""改编来源：https://github.com/fr3kchy/ollama-local-rag-demo
原始文件：ingest.py:embed_texts(); query.py:embed_query()
commit：2d4a5d30b4a4829a007b8132e11cea71282a83d7
MIT License，完整版权声明见 licenses/。
修改：保留 HTTP 循环；显式配置；统一归一化；拒绝 NaN/Inf/零向量；动态维度。
"""
import httpx
import numpy as np

def embed_texts(texts: list[str], model="nomic-embed-text", base_url="http://localhost:11434", timeout=120) -> np.ndarray:
    """Call Ollama /api/embeddings once per text. Returns (N, actual_dimension) float32."""
    if not texts or any(not isinstance(t, str) or not t.strip() for t in texts):
        raise ValueError("Nonempty texts required")
    vectors: list[list[float]] = []
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        for t in texts:
            r = client.post("/api/embeddings", json={"model": model, "prompt": t})
            r.raise_for_status()
            vectors.append(r.json()["embedding"])
    return normalize_vectors(vectors)


def normalize_vectors(vectors):
    arr = np.asarray(vectors, dtype="float32")
    if arr.ndim != 2 or min(arr.shape) == 0 or not np.isfinite(arr).all():
        raise ValueError("Embedding must be a nonempty finite 2D array")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or (norms == 0).any():
        raise ValueError("Zero or invalid embedding vector")
    return np.ascontiguousarray(arr / norms)


def embed_query(text: str, **kwargs):
    # 由 query.py:embed_query 改编，统一调用文档编码函数避免规则分叉。
    return embed_texts([text], **kwargs).reshape(1, -1)
