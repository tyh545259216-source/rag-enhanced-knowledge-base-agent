"""在 nanobot .venv 运行；只测试插件和直接调用，不启动 Agent。"""
import asyncio,hashlib,json,importlib.metadata as metadata,shutil,socket,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from nanobot.agent.tools.loader import ToolLoader
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.context import ToolContext
from nanobot.config.schema import ToolsConfig
from nanobot.agent.tools.base import ToolResult
from knowledge_base_agent.tools.search_knowledge_base import SearchKnowledgeBaseTool

ROOT=Path(__file__).resolve().parents[1]
(ROOT/"artifacts").mkdir(exist_ok=True)

class PluginTests(unittest.TestCase):
    def result(self,tool,**kwargs):return asyncio.run(tool.execute(**kwargs))
    def assert_error(self,result):
        self.assertIsInstance(result,ToolResult);self.assertTrue(result.is_error)

    def test_entry_point(self):
        eps=list(metadata.entry_points(group="nanobot.tools"))
        ep=next(e for e in eps if e.name=="search_knowledge_base")
        self.assertIs(ep.load(),SearchKnowledgeBaseTool)

    def test_loader_registry_schema(self):
        loader=ToolLoader(test_classes=[])
        registry=ToolRegistry()
        names=loader.load(ToolContext(config=ToolsConfig(),workspace=str(ROOT)),registry)
        self.assertIn("search_knowledge_base",names)
        self.assertTrue(registry.get("search_knowledge_base").read_only)
        schema=next(s for s in registry.get_definitions() if s["function"]["name"]=="search_knowledge_base")
        self.assertEqual(schema["function"]["parameters"]["required"],["query"])
        self.assertEqual(schema["function"]["parameters"]["properties"]["top_k"]["default"],3)
        (ROOT/"artifacts/plugin_schema.json").write_text(json.dumps(schema,indent=2,ensure_ascii=False),encoding="utf-8")

    def test_real_direct_registry_baseline(self):
        registry=ToolRegistry();ToolLoader(test_classes=[]).load(ToolContext(config=ToolsConfig(),workspace=str(ROOT)),registry)
        baseline=json.loads((ROOT/"docs/evidence/eval/retrieval_baseline.json").read_text(encoding="utf-8"))["queries"][0]
        result=asyncio.run(registry.execute("search_knowledge_base",{"query":baseline["query"]}))
        self.assertIsInstance(result,ToolResult);self.assertFalse(result.is_error)
        actual=json.loads(result)["results"];expected=baseline["results"][:3]
        self.assertEqual(len(actual),3)
        for got,want in zip(actual,expected):
            for key in ["rank","text","source","chunk_id","page"]:self.assertEqual(got[key],want[key])
            self.assertAlmostEqual(got["score"],want["score"],places=6)
        (ROOT/"artifacts/plugin_direct_tool_result.json").write_text(str(result),encoding="utf-8")

    def test_empty_query(self):
        for q in ["","   "]:self.assert_error(self.result(SearchKnowledgeBaseTool(),query=q))

    def test_nonpositive_k(self):
        for k in [0,-1]:self.assert_error(self.result(SearchKnowledgeBaseTool(),query="Aurora",top_k=k))

    def test_above_limit(self):
        result=self.result(SearchKnowledgeBaseTool(),query="Aurora",top_k=11)
        self.assert_error(result);self.assertEqual(json.loads(result)["error"],"invalid_arguments")

    def test_bad_types(self):
        for q,k in [(None,3),("Aurora",True),("Aurora",1.5)]:self.assert_error(self.result(SearchKnowledgeBaseTool(),query=q,top_k=k))

    def make_config(self,temporary,url="http://localhost:11434",copy_store=False):
        root=Path(temporary);store=root/"store"
        if copy_store:shutil.copytree(ROOT/"store",store)
        cfg={"data_dir":str(ROOT/"data"),"store_dir":str(store),"embedding_model":"nomic-embed-text",
             "base_url":url,"chunk_size":160,"overlap":24,"timeout":1}
        path=root/"config.yaml";path.write_text(json.dumps(cfg),encoding="utf-8");return path

    def test_missing_index(self):
        with tempfile.TemporaryDirectory() as d:
            result=self.result(SearchKnowledgeBaseTool(self.make_config(d)),query="Aurora")
            self.assert_error(result);self.assertEqual(json.loads(result)["exception_type"],"FileNotFoundError")

    def test_metadata_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            config=self.make_config(d,copy_store=True)
            (Path(d)/"store/metadata.json").write_text("[]",encoding="utf-8")
            result=self.result(SearchKnowledgeBaseTool(config),query="Aurora")
            self.assert_error(result);self.assertEqual(json.loads(result)["exception_type"],"ValueError")

    def test_ollama_unavailable(self):
        # 仅临时测试端口，不修改或关闭真实 Ollama。
        with tempfile.TemporaryDirectory() as d, socket.socket() as sock:
            sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
            config=self.make_config(d,url=f"http://127.0.0.1:{port}",copy_store=True)
            result=self.result(SearchKnowledgeBaseTool(config),query="Aurora")
            self.assert_error(result);self.assertEqual(json.loads(result)["error"],"embedding_unavailable")

    def test_frozen_artifacts(self):
        before=json.loads((ROOT/"docs/releases/frozen_core.json").read_text())
        for path,digest in before.items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)

if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PluginTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={"tests_run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"success":result.wasSuccessful()}
    (ROOT/"artifacts/plugin_test_results.json").write_text(json.dumps(report,indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
