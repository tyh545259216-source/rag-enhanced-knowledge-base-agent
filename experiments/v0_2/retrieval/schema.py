"""实验统一返回值。不同 score_kind 的数值不能相加或横向当作相似度。"""
from dataclasses import dataclass, replace
import math

@dataclass(frozen=True)
class RankedResult:
    chunk_id: str
    rank: int
    score: float
    source: str
    text: str
    page: int | None
    score_kind: str

def validate_search(query, top_k):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be nonempty string")
    if type(top_k) is not int or top_k <= 0:
        raise ValueError("top_k must be positive integer")

def validate_chunks(chunks):
    ids = [c["chunk_id"] for c in chunks]
    if not chunks or len(set(ids)) != len(ids):
        raise ValueError("nonempty chunks with unique IDs required")
    for c in chunks:
        if not all(isinstance(c.get(k), str) and c[k].strip()
                   for k in ("chunk_id", "text", "source")):
            raise ValueError("invalid chunk fields")

def reciprocal_rank_fusion(rank_lists, k=60):
    """按1-based rank融合，只使用排名；缺席某列表贡献为0。"""
    if type(k) is not int or k <= 0:
        raise ValueError("RRF k must be positive integer")
    scores, docs = {}, {}
    for results in rank_lists:
        seen = set()
        for rank, result in enumerate(results, 1):
            if result.chunk_id in seen or result.rank != rank or not math.isfinite(result.score):
                raise ValueError("rank list must contain unique IDs and contiguous ranks")
            seen.add(result.chunk_id)
            if result.chunk_id in docs:
                previous = docs[result.chunk_id]
                if (previous.source, previous.text, previous.page) != (result.source, result.text, result.page):
                    raise ValueError("same ID has conflicting metadata")
            docs[result.chunk_id] = result
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + 1/(k+rank)
    ordered = sorted(scores, key=lambda ident: (-scores[ident], ident))
    return [replace(docs[ident], rank=rank, score=scores[ident], score_kind="rrf")
            for rank, ident in enumerate(ordered, 1)]
