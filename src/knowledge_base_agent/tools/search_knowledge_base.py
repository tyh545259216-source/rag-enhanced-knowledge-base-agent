"""nanobot 外部只读工具：只委托冻结的 Retriever，不调用生成模型。"""
import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path
import httpx
from nanobot.agent.tools.base import Tool, ToolResult
from knowledge_base_agent.rag.config import load_config
from knowledge_base_agent.rag.adapter import RAGAdapter
from knowledge_base_agent.rag.retriever import Retriever


class SearchKnowledgeBaseTool(Tool):
    MAX_TOP_K = 10

    def __init__(self, config_path=None):
        # 独立插件配置，绝不读取或修改 nanobot Provider/OAuth。
        self.config_path = Path(config_path or os.environ.get("KNOWLEDGE_BASE_CONFIG")
                                or Path(__file__).resolve().parents[3] / "config.yaml").resolve()
        self._retriever = None
        self._lock = asyncio.Lock()

    @property
    def name(self): return "search_knowledge_base"

    @property
    def description(self):
        return "Search the local internal knowledge base. Return evidence with sources and scores, not a final answer. Nearest neighbors may not answer the question."

    @property
    def read_only(self): return True

    @property
    def concurrency_safe(self): return False

    @property
    def parameters(self):
        return {"type":"object", "properties":{
            "query":{"type":"string", "minLength":1, "description":"Knowledge base search query"},
            "top_k":{"type":"integer", "default":3, "minimum":1, "maximum":self.MAX_TOP_K}},
            "required":["query"], "additionalProperties":False}

    def _search(self, query, top_k):
        if self._retriever is None:
            adapter = RAGAdapter(load_config(self.config_path))
            if not adapter.load():
                raise FileNotFoundError("Knowledge base index is missing; ingest separately")
            self._retriever = Retriever(adapter)
        results = self._retriever.search(query, top_k)
        return ToolResult(json.dumps({"results":[dict(rank=i, **asdict(item))
                                                 for i,item in enumerate(results,1)]},ensure_ascii=False))

    async def execute(self, query: str, top_k: int = 3):
        errors = self.validate_params({"query":query,"top_k":top_k})
        if errors or not query.strip():
            return ToolResult.error(json.dumps({"error":"invalid_arguments", "detail":errors or ["query must not be blank"]},ensure_ascii=False))
        # 同实例串行，避免惰性初始化和 Retriever.last_latency 互相覆盖。
        async with self._lock:
            try:
                return await asyncio.to_thread(self._search, query, top_k)
            except httpx.HTTPError as exc:
                return ToolResult.error(json.dumps({"error":"embedding_unavailable", "exception_type":type(exc).__name__}))
            except (OSError, ValueError, KeyError, RuntimeError) as exc:
                return ToolResult.error(json.dumps({"error":"knowledge_base_unavailable", "exception_type":type(exc).__name__, "detail":str(exc)},ensure_ascii=False))
