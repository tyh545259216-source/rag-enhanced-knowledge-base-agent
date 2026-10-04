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

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"phase3a"
sys.stdout.reconfigure(encoding="utf-8");logger.remove()

def frozen():
    files=list((ROOT/"src").rglob("*.py"))+list((ROOT/"data").glob("*"))+list((ROOT/"store").glob("*"))+list((ROOT/"eval").glob("*"))+[ROOT/"config.yaml",ROOT/"pyproject.toml"]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}

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
    if len(active["requests"])>=2:raise RuntimeError("At most two model requests per case")
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
        active["parsed_tool_calls"]=[{"id":t.id,"name":t.name,"arguments":t.arguments} for t in ctx.tool_calls]
        if len(active["requests"])!=1 or not active["requests"][0]["raw_tool_call_deltas"]:
            raise RuntimeError("No native first-round structured tool call or unexpected repeated tool call")
        if len(ctx.tool_calls)!=1 or ctx.tool_calls[0].name!="search_knowledge_base":
            raise RuntimeError("Only one search_knowledge_base call is allowed")
    async def before_execute_tool(self,ctx,call,tool,params):
        active["tool_start"]=time.perf_counter();active["registry_tool_type"]=type(tool).__name__;active["executed_arguments"]=params
    async def after_execute_tool(self,ctx,call,tool,params,result):
        active["retrieval_latency_ms"]=(time.perf_counter()-active.pop("tool_start"))*1000
        active["tool_result"]={"is_error":getattr(result,"is_error",False),"content":str(result)}
        wrapped=getattr(tool,"_wrapped",tool)
        if wrapped._retriever:active["retriever_latency"]=wrapped._retriever.adapter.last_latency
    async def after_iteration(self,ctx):
        active.setdefault("parsed_responses",[]).append({"iteration":ctx.iteration,"finish_reason":ctx.response.finish_reason,"content":ctx.response.content})
        if len(active["requests"])==1 and not ctx.response.tool_calls:
            raise RuntimeError("Model did not generate structured tool calls")

async def no_compaction(history,summary):raise RuntimeError("No memory writes permitted")

def transport(case):
    if len(case["requests"])<2:return False
    messages=case["requests"][1]["messages"]
    case["second_roles"]=[m["role"] for m in messages]
    calls=[c for m in messages if m["role"]=="assistant" for c in m.get("tool_calls",[])]
    tools=[m for m in messages if m["role"]=="tool"]
    return len(calls)==len(tools)==1 and calls[0]["id"]==tools[0]["tool_call_id"] and tools[0]["content"]==case["tool_result"]["content"]

async def main():
    global active
    before=frozen();(OUT/("retest_frozen_before.json" if "--case3-only" in sys.argv else "frozen_before.json")).write_text(json.dumps(before,indent=2),encoding="utf-8")
    registry=ToolRegistry();loader=ToolLoader(test_classes=[])
    registered=loader.load(ToolContext(config=ToolsConfig(),workspace=str(ROOT)),registry)
    assert "search_knowledge_base" in registered
    config=resolve_config_env_vars(load_config());preset=config.resolve_preset("qwen")
    assert preset.provider=="ollama" and preset.model=="qwen3:1.7b"
    provider=_make_provider_core(config,preset=preset)
    runtime=LLMRuntime.capture(provider,preset.model,context_window_tokens=preset.context_window_tokens,model_preset="qwen")
    old=json.loads((ROOT/"eval/search_results.json").read_text(encoding="utf-8"))["queries"]
    baseline=json.loads((ROOT/"eval/retrieval_baseline.json").read_text(encoding="utf-8"))["queries"]
    cases=[(old[0]["query"],old[0]["results"]),(old[1]["query"],old[1]["results"]),(next(x for x in baseline if x["id"]=="q28")["query"],next(x for x in baseline if x["id"]=="q28")["results"][:3])]
    report={"timestamp":datetime.now().astimezone().isoformat(),"registered":registered,"provider_class":type(provider).__name__,"cases":[]}
    for number,(question,expected) in enumerate(cases,1):
        if "--case3-only" in sys.argv and number != 3:continue
        active={"case":number,"question":question,"requests":[],"expected_top3":expected}
        report["cases"].append(active);start=time.perf_counter()
        messages=[{"role":"system","content":"本轮必须先调用 search_knowledge_base，query 原样使用用户的问题，top_k=3。收到结果后仅依据返回证据回答；区分项目负责人和验收负责人，缺少所问事实时回答根据当前资料无法确定。只查询一次。"}, {"role":"user","content":question}]
        try:
            result=await asyncio.wait_for(AgentRunner().run(AgentRunSpec(initial_messages=messages,tools=registry,runtime=runtime,max_iterations=2,max_tool_result_chars=12000,hook=ObserveHook(reraise=True),workspace=ROOT,consolidate_history=no_compaction,finalize_on_max_iterations=False)),timeout=300)
            active["final_answer"]=result.final_content;active["stop_reason"]=result.stop_reason
        except Exception as exc:
            chain=[];current=exc
            while current:
                chain.append({"type":type(current).__name__,"message":str(current)})
                current=current.__cause__ or current.__context__
            active["errors"]=chain
        active["e2e_latency_ms"]=(time.perf_counter()-start)*1000
        active["transport_correct"]=transport(active)
        actual=json.loads(active.get("tool_result",{}).get("content",'{"results":[]}')).get("results",[])
        active["baseline_matches"]=len(actual)==len(expected) and all(all(x[k]==y[k] for k in ["rank","text","source","chunk_id","page"]) and abs(x["score"]-y["score"])<1e-6 for x,y in zip(actual,expected))
        active["integration_success"]=bool(active.get("transport_correct") and active.get("parsed_tool_calls") and len(active["requests"])==2 and all(x.get("http_status")==200 for x in active["requests"]) and active.get("stop_reason")=="completed")
        (OUT/("case3_retest.json" if "--case3-only" in sys.argv else "trace.json")).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps({k:v for k,v in active.items() if k in ["case","parsed_tool_calls","final_answer","integration_success","baseline_matches","e2e_latency_ms","errors"]},ensure_ascii=False),flush=True)
    report["frozen_files_unchanged"]=before==frozen();assert report["frozen_files_unchanged"]
    (OUT/("retest_frozen_after.json" if "--case3-only" in sys.argv else "frozen_after.json")).write_text(json.dumps(frozen(),indent=2),encoding="utf-8")
    (OUT/("case3_retest.json" if "--case3-only" in sys.argv else "trace.json")).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__":asyncio.run(main())
