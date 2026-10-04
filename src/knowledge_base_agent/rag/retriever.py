from .adapter import RAGAdapter
from .schemas import SearchResult

class Retriever:
    def __init__(self, adapter: RAGAdapter):
        self.adapter = adapter

    def search(self, query: str, top_k: int = 3) -> list[SearchResult]:
        # 不设置未校准的相似度阈值；无效输入在 HTTP 请求之前拒绝。
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be nonempty string")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be positive integer")
        return self.adapter.search(query.strip(), top_k)
