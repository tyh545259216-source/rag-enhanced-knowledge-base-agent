"""只做观测：复用现有 AgentRunner 和外部工具，不指定模型的 tool_calls。"""
import asyncio,hashlib,json,sys,time
from pathlib import Path
from datetime import datetime
import httpx
from loguru import logger
from nanobot.config.loader import load_config,resolve_config_env_vars
from nanobot.config.schema import ToolsConfig
from nanobot.providers.factory import _make_provider_core
from nanobot.utils.llm_runtime import LLMRuntime
from nanobot.agent.runner import AgentRunner,AgentRunSpec
from nanobot.agent.hook import AgentHook
from nanobot.agent.tools.loader import ToolLoader
from nanobot.agent.tools.context import ToolContext
from nanobot.agent.tools.registry import ToolRegistry

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts"/"v1_smoke";OUT.mkdir(parents=True,exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8");logger.remove()

def frozen():
    paths=list((ROOT/"src/knowledge_base_agent").rglob("*.py"))+list((ROOT/"data").glob("*"))+list((ROOT/"store").glob("*"))+[ROOT/"config.yaml"]
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}

active=None;original=httpx.AsyncClient.send
class ObservedStream(httpx.AsyncByteStream):
    def __init__(self,inner,record,start):self.inner=inner;self.record=record;self.start=start;self.buffer=""
    async def __aiter__(self):
        try:
            async for part in self.inner:
                self.buffer+=part.decode("utf-8",errors="replace")
                while "\n" in self.buffer:
                    line,self.buffer=self.buffer.split("\n",1)
                    if line.startswith("data: "):
                        try:
                            data=json.loads(line[6:])
                            for choice in data.get("choices",[]):
                                if choice.get("delta",{}).get("tool_calls"):
                                    self.record["raw_tool_call_deltas"].extend(choice["delta"]["tool_calls"])
                                if choice.get("finish_reason"):
                                    self.record["wire_finish_reason"]=choice["finish_reason"]
                                    self.record["latency_ms"]=(time.perf_counter()-self.start)*1000
                        except json.JSONDecodeError:pass
                yield part
        finally:self.record["latency_ms"]=(time.perf_counter()-self.start)*1000
    async def aclose(self):await self.inner.aclose()

async def observed_send(self,request,*args,**kwargs):
    if not request.url.path.endswith("/chat/completions"):return await original(self,request,*args,**kwargs)
    if len(active["requests"])>=4:raise RuntimeError("At most four model requests per case")
    body=json.loads(request.content)
    assert request.url.host=="localhost" and body["model"]=="qwen3:1.7b"
    record={"endpoint":str(request.url),"model":body["model"],"messages":body["messages"],"tools":body.get("tools"),"raw_tool_call_deltas":[]}
    active["requests"].append(record);start=time.perf_counter()
    response=await original(self,request,*args,**kwargs)
    record["http_status"]=response.status_code;record["headers_latency_ms"]=(time.perf_counter()-start)*1000
    response.stream=ObservedStream(response.stream,record,start)
    return response
httpx.AsyncClient.send=observed_send


class ObserveHook(AgentHook):
    async def before_execute_tools(self,ctx):
        calls=[{"id":t.id,"name":t.name,"arguments":t.arguments,"request_index":len(active["requests"]),
                "native_structured":bool(active["requests"][-1]["raw_tool_call_deltas"])} for t in ctx.tool_calls]
        active.setdefault("tool_calls",[]).extend(calls)
    async def before_execute_tool(self,ctx,call,tool,params):
        # 安全范围约束，不根据题目类别触发或禁止知识库查询。
        if call.name!="search_knowledge_base":raise RuntimeError("Unapproved tool blocked")
        active.setdefault("tool_starts",{})[call.id]=time.perf_counter()
    async def after_execute_tool(self,ctx,call,tool,params,result):
        wrapped=getattr(tool,"_wrapped",tool)
        event={"tool_call_id":call.id,"name":call.name,"arguments":params,"is_error":getattr(result,"is_error",False),"content":str(result),
               "latency_ms":(time.perf_counter()-active["tool_starts"].pop(call.id))*1000}
        if getattr(wrapped,"_retriever",None):event["retriever_latency"]=dict(wrapped._retriever.adapter.last_latency)
        active.setdefault("tool_results",[]).append(event)
    async def after_iteration(self,ctx):
        active.setdefault("responses",[]).append({"iteration":ctx.iteration,"finish_reason":ctx.response.finish_reason,"content":ctx.response.content})

async def no_compaction(history,summary):raise RuntimeError("No memory writes permitted")

async def main():
    global active
    before=frozen();(OUT/"frozen_before.json").write_text(json.dumps(before,indent=2),encoding="utf-8")
    # 仅发现/注册一个明确授权的外部只读工具，不加载任何内置工具。
    registry=ToolRegistry();loader=ToolLoader(test_classes=[])
    cls=loader._discover_plugins()["search_knowledge_base"]
    loader._plugins={"search_knowledge_base":cls}
    registered=loader.load(ToolContext(config=ToolsConfig(),workspace=str(ROOT)),registry)
    assert registered==["search_knowledge_base"]
    assert registry.get("search_knowledge_base").read_only
    assert [x["function"]["name"] for x in registry.get_definitions()]==["search_knowledge_base"]
    print("AVAILABLE_TOOLS",registered,flush=True)
    config=resolve_config_env_vars(load_config());preset=config.resolve_preset("qwen")
    assert preset.provider=="ollama" and preset.model=="qwen3:1.7b"
    provider=_make_provider_core(config,preset=preset)
    runtime=LLMRuntime.capture(provider,preset.model,context_window_tokens=preset.context_window_tokens,model_preset="qwen")
    dataset=json.loads((ROOT/"docs/releases/smoke_cases.json").read_text(encoding="utf-8"))
    report={"timestamp":datetime.now().astimezone().isoformat(),"registered":registered,"provider_class":type(provider).__name__,
            "dataset_sha256":hashlib.sha256((ROOT/"docs/releases/smoke_cases.json").read_bytes()).hexdigest(),
            "system_instruction":dataset["system_instruction"],"max_iterations":4,"cases":[]}
    for item in dataset["items"]:
        active={**item,"requests":[],"tool_calls":[],"tool_results":[]};report["cases"].append(active);start=time.perf_counter()
        messages=[{"role":"system","content":dataset["system_instruction"]},{"role":"user","content":item["question"]}]
        try:
            result=await asyncio.wait_for(AgentRunner().run(AgentRunSpec(initial_messages=messages,tools=registry,runtime=runtime,max_iterations=4,max_tool_result_chars=12000,hook=ObserveHook(reraise=True),workspace=ROOT,consolidate_history=no_compaction,finalize_on_max_iterations=False)),timeout=300)
            active["final_answer"]=result.final_content;active["stop_reason"]=result.stop_reason
        except Exception as exc:
            active["error"]={"type":type(exc).__name__,"message":str(exc)}
        active.pop("tool_starts",None)
        active["total_latency_ms"]=(time.perf_counter()-start)*1000
        active["llm_request_count"]=len(active["requests"])
        active["actual_tools"]=[t["name"] for t in active["tool_calls"]]
        (OUT/"trace.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps({k:active.get(k) for k in ['id','category','expected_tool','actual_tools','llm_request_count','final_answer','total_latency_ms','error']},ensure_ascii=False),flush=True)
    report["frozen_files_unchanged"]=before==frozen();assert report["frozen_files_unchanged"]
    (OUT/"frozen_after.json").write_text(json.dumps(frozen(),indent=2),encoding="utf-8")
    (OUT/"trace.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__":asyncio.run(main())
