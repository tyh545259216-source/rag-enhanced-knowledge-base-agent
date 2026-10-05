"""只观测HTTP/SSE和nanobot hooks；不合成模型返回或工具调用。"""
import codecs,json,time
from contextlib import contextmanager
import httpx
from nanobot.agent.hook import AgentHook
from nanobot.agent.tools.base import Tool
from .config import TOOL

class DescriptionTool(Tool):
    def __init__(self,wrapped,description):self.wrapped=wrapped;self.text=description
    @property
    def name(self):return self.wrapped.name
    @property
    def description(self):return self.text
    @property
    def parameters(self):return self.wrapped.parameters
    @property
    def read_only(self):return self.wrapped.read_only
    @property
    def concurrency_safe(self):return self.wrapped.concurrency_safe
    async def execute(self,**params):return await self.wrapped.execute(**params)

class ObservedStream(httpx.AsyncByteStream):
    def __init__(self,inner,record,start):
        self.inner=inner;self.record=record;self.start=start;self.buffer=""
        self.decoder=codecs.getincrementaldecoder("utf-8")()
    async def __aiter__(self):
        try:
            async for part in self.inner:
                self.buffer+=self.decoder.decode(part)
                while "\n" in self.buffer:
                    line,self.buffer=self.buffer.split("\n",1)
                    if line.startswith("data: "):
                        try:
                            payload=json.loads(line[6:])
                            for choice in payload.get("choices",[]):
                                delta=choice.get("delta",{})
                                self.record["raw_tool_call_deltas"].extend(delta.get("tool_calls",[]))
                                self.record["wire_content"]+=delta.get("content") or ""
                                if choice.get("finish_reason"):
                                    self.record["finish_reason"]=choice["finish_reason"]
                                    self.record.setdefault("latency_ms",(time.perf_counter()-self.start)*1000)
                        except json.JSONDecodeError:pass
                yield part
        finally:self.record.setdefault("latency_ms",(time.perf_counter()-self.start)*1000)
    async def aclose(self):
        self.record.setdefault("latency_ms",(time.perf_counter()-self.start)*1000)
        await self.inner.aclose()

@contextmanager
def observe_http(case,arm):
    original=httpx.AsyncClient.send
    async def send(client,request,*args,**kwargs):
        # 只记录本地Ollama模型请求，绝不读取/输出Authorization或cookies。
        if request.url.path!="/v1/chat/completions":return await original(client,request,*args,**kwargs)
        if request.url.host!="localhost" or request.url.port!=11434:raise RuntimeError("unexpected model endpoint")
        body=json.loads(request.content)
        if body["model"]!=arm["model"]:raise RuntimeError("unexpected model")
        record={"endpoint":str(request.url),"model":body["model"],"messages":body["messages"],"tools":body.get("tools"),
                "generation":{k:body.get(k) for k in ("temperature","max_tokens","reasoning_effort","stream")},
                "tool_choice":body.get("tool_choice"),"raw_tool_call_deltas":[],"wire_content":""}
        case["requests"].append(record);start=time.perf_counter()
        try:
            response=await original(client,request,*args,**kwargs)
            record["http_status"]=response.status_code
            record["header_latency_ms"]=(time.perf_counter()-start)*1000
            response.stream=ObservedStream(response.stream,record,start)
            return response
        except BaseException as exc:
            record["error_type"]=type(exc).__name__;record["latency_ms"]=(time.perf_counter()-start)*1000
            raise
    httpx.AsyncClient.send=send
    try:yield
    finally:httpx.AsyncClient.send=original

class ObserveHook(AgentHook):
    def __init__(self,case):super().__init__(reraise=True);self.case=case;self.starts={}
    async def before_execute_tools(self,ctx):
        last=self.case["requests"][-1] if self.case["requests"] else {}
        for call in ctx.tool_calls:
            self.case["tool_calls"].append({"id":call.id,"name":call.name,"arguments":call.arguments,
                 "request_index":len(self.case["requests"]),"native_structured":bool(last.get("raw_tool_call_deltas"))})
    async def before_execute_tool(self,ctx,call,tool,params):
        if call.name!=TOOL or not tool.read_only:raise RuntimeError("only read-only KB tool is allowed")
        self.starts[call.id]=time.perf_counter()
    async def after_execute_tool(self,ctx,call,tool,params,result):
        self.case["tool_results"].append({"tool_call_id":call.id,"name":call.name,"arguments":params,
          "content":str(result),"is_error":getattr(result,"is_error",False),
          "latency_ms":(time.perf_counter()-self.starts.pop(call.id))*1000})
    async def after_iteration(self,ctx):
        self.case["responses"].append({"iteration":ctx.iteration,"finish_reason":ctx.response.finish_reason,
              "content":ctx.response.content,"tool_names":[c.name for c in ctx.response.tool_calls]})
