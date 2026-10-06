"""真实nanobot执行链。每题独立上下文，逐题写不可覆盖trace；不按标签路由。"""
import argparse,asyncio,hashlib,inspect,json,os,sys,time,traceback
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
import httpx
from loguru import logger
from nanobot.agent.runner import AgentRunner,AgentRunSpec
from nanobot.agent.tools.loader import ToolLoader
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.context import ToolContext
from nanobot.config.schema import ToolsConfig
from nanobot.config.loader import load_config,resolve_config_env_vars
from nanobot.providers.factory import _make_provider_core
from nanobot.utils.llm_runtime import LLMRuntime
from experiments.v0_2.datasets import load_bundle
from experiments.v0_2.retrieval.runner import protected_hashes,verify_integrity,digest,source_hashes as retrieval_sources
from .config import TOOL,BASE_SETTINGS,SELECTION_POLICY,baseline,validate_arm,canonical_hash,write_once
from .evaluate import summarize,confusion
from .observe import DescriptionTool,ObserveHook,observe_http
ROOT=Path(__file__).resolve().parents[3]
PHASE2=ROOT/"artifacts/v0.2/retrieval/phase2_first_20261005"
CONFIG_PATH=ROOT/"experiments/v0_2/routing/ROUTING_CONFIG.json"

@contextmanager
def temporary_kb_config(path):
    key="KNOWLEDGE_BASE_CONFIG";old=os.environ.get(key)
    os.environ[key]=str(path)
    try:yield
    finally:
        if old is None:os.environ.pop(key,None)
        else:os.environ[key]=old

def discover_tool(config_path,description):
    loader=ToolLoader(test_classes=[]);registry=ToolRegistry()
    cls=loader._discover_plugins()[TOOL]
    expected=ROOT/"src/knowledge_base_agent/tools/search_knowledge_base.py"
    if Path(inspect.getfile(cls)).resolve()!=expected.resolve():raise ValueError("wrong plugin provenance")
    loader._plugins={TOOL:cls}
    with temporary_kb_config(config_path):
        registered=loader.load(ToolContext(config=ToolsConfig(),workspace=str(ROOT)),registry)
    if registered!=[TOOL] or not registry.get(TOOL).read_only:raise ValueError("unexpected tools")
    original=registry.get(TOOL)
    registry.register(DescriptionTool(original,description))
    return registry

def make_runtime():
    config=resolve_config_env_vars(load_config());preset=config.resolve_preset("qwen")
    if preset.provider!="ollama" or preset.model!=BASE_SETTINGS["model"]:raise ValueError("unexpected saved provider/model")
    provider=_make_provider_core(config,preset=preset)
    runtime=LLMRuntime.capture(provider,preset.model,context_window_tokens=preset.context_window_tokens,model_preset="qwen")
    g=asdict(runtime.generation)
    for key in ("temperature","max_tokens","reasoning_effort"):
        if g[key]!=BASE_SETTINGS[key]:raise ValueError(f"current saved generation differs: {key}")
    if provider.api_base!="http://localhost:11434/v1" or getattr(provider,"_extra_body",{}):
        raise ValueError("unexpected endpoint/extra generation options")
    if runtime.context_window_tokens!=BASE_SETTINGS["context_window_tokens"]:raise ValueError("context window changed")
    return runtime

def routing_sources():
    paths=list((ROOT/"experiments/v0_2/routing").glob("*.py"))
    paths+=[ROOT/"scripts/v0_2/run_routing.py",ROOT/"scripts/v0_2/report_routing.py",ROOT/"tests/v0_2/test_routing.py"]
    return {p.relative_to(ROOT).as_posix():digest(p) for p in paths if p.is_file()}

def verify_run(run_dir):
    bundle,_=verify_integrity(json.loads((run_dir/"integrity_before.json").read_text(encoding="utf-8")))
    initial=json.loads((run_dir/"protection.json").read_text(encoding="utf-8"))
    for f,h in initial["phase2_raw_files"].items():
        if digest(PHASE2/f)!=h:raise ValueError(f"Phase2 changed: {f}")
    if digest(ROOT/"eval/v0.2/freeze_manifest.json")!=initial["dataset_manifest_sha256"]:
        raise ValueError("dataset manifest changed")
    tags=httpx.get("http://localhost:11434/api/tags",timeout=30)
    tags.raise_for_status()
    models={m["name"]:{k:m.get(k) for k in ("name","digest","size")} for m in tags.json()["models"] if m["name"] in initial["model_metadata"]}
    if models!=initial["model_metadata"]:raise ValueError("Ollama model metadata changed")
    return bundle

def initialize(run_dir):
    if run_dir.exists():raise FileExistsError("new run directory required")
    bundle,protected=verify_integrity()
    phase2lock=json.loads((PHASE2/"lock.json").read_text(encoding="utf-8"))
    if retrieval_sources()!=phase2lock["source_hashes"]:raise ValueError("Phase2 implementation changed")
    info=json.loads((PHASE2/"index/index_info.json").read_text(encoding="utf-8"))
    if info["chunk_count"]!=40 or info["index_type"]!="IndexFlatIP" or not info["normalized"]:raise ValueError("wrong frozen Dense index")
    runtime=make_runtime()
    tags=httpx.get("http://localhost:11434/api/tags",timeout=30).json()["models"]
    models={m["name"]:{k:m.get(k) for k in ("name","digest","size")} for m in tags
            if m["name"] in {"qwen3:1.7b","nomic-embed-text:latest"}}
    if len(models)!=2:raise ValueError("required models missing")
    run_dir.mkdir(parents=True)
    rag={"data_dir":os.path.relpath(ROOT/"eval/v0.2/corpus",run_dir),
         "store_dir":os.path.relpath(PHASE2/"index",run_dir),"embedding_model":"nomic-embed-text",
         "base_url":"http://localhost:11434","chunk_size":160,"overlap":24,"timeout":120}
    write_once(run_dir/"plugin_rag_config.json",rag)
    registry=discover_tool(run_dir/"plugin_rag_config.json",baseline()["tool_description"])
    schema=registry.get_definitions()[0]
    write_once(run_dir/"integrity_before.json",protected)
    write_once(run_dir/"protection.json",{
        "phase2_raw_files":{p.relative_to(PHASE2).as_posix():digest(p) for p in PHASE2.rglob("*") if p.is_file()},
        "dataset_manifest_sha256":digest(ROOT/"eval/v0.2/freeze_manifest.json"),
        "model_metadata":models})
    write_once(run_dir/"preregistration.json",{"created_at_utc":datetime.now(timezone.utc).isoformat(),
        "runtime_repository_head":"86c7325736de5c5a317ce8c59cb1178758dced80",
        "baseline":baseline(),"selection_policy":SELECTION_POLICY,"tool_parameters_sha256":canonical_hash(schema["function"]["parameters"]),
        "formal_test":"A0 plus selected arm, each 20 once; selected is primary; if selected=A0 run only A0",
        "context_reset":"new AgentRunner and registry per question; no memory/session persistence",
        "error_policy":"retain errors and first attempts; no manual rerun for better metrics",
        "index":"Phase2 frozen Dense 40 chunks; default plugin configuration unchanged",
        "generation_seed":"not added; saved nanobot generation retained; no deterministic cross-machine claim"})

async def no_compaction(*args):raise RuntimeError("memory/compaction writes prohibited")

async def one_case(item,arm,runtime,run_dir):
    # 模型输入只有question；golden category/expected labels仅用于事后记录与评估。
    registry=discover_tool(run_dir/"plugin_rag_config.json",arm["tool_description"])
    prereg=json.loads((run_dir/"preregistration.json").read_text(encoding="utf-8"))
    schema=registry.get_definitions()[0]
    if canonical_hash(schema["function"]["parameters"])!=prereg["tool_parameters_sha256"]:
        raise ValueError("tool argument schema changed")
    case={"id":item["id"],"category":item["category"],"query":item["query"],"split":item["split"],"arm":arm["arm"],
          "expected_tool":item["expected_tool"],"expected_use_tool":item["expected_tool"]==TOOL,
          "requests":[],"tool_calls":[],"tool_results":[],"responses":[],
          "started_at_utc":datetime.now(timezone.utc).isoformat()}
    messages=[{"role":"system","content":arm["system_instruction"]},{"role":"user","content":item["query"]}]
    start=time.perf_counter()
    with observe_http(case,arm):
        try:
            result=await asyncio.wait_for(AgentRunner().run(AgentRunSpec(
                initial_messages=messages,tools=registry,runtime=runtime,max_iterations=arm["max_iterations"],
                max_tool_result_chars=arm["max_tool_result_chars"],hook=ObserveHook(case),
                workspace=ROOT,consolidate_history=no_compaction,provider_retry_mode=arm["provider_retry_mode"],
                finalize_on_max_iterations=arm["finalize_on_max_iterations"])),timeout=arm["case_timeout_seconds"])
            case["final_response"]=result.final_content;case["stop_reason"]=result.stop_reason
            case["error"]=result.error;case["failure_error_kind"]=result.failure_error_kind
            case["final_message_roles"]=[m["role"] for m in result.messages]
        except Exception as exc:
            case["error"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
            case["final_response"]=None
    case["latency_ms"]=(time.perf_counter()-start)*1000
    case["actual_use_tool"]=any(c["name"]==TOOL for c in case["tool_calls"])
    case["confusion"]=confusion(case["expected_use_tool"],case["actual_use_tool"])
    case["llm_request_count"]=len(case["requests"])
    return case

async def run_arm(run_dir,split,arm,selected_ids=None):
    validate_arm(arm);bundle=verify_run(run_dir);runtime=make_runtime()
    folder=run_dir/split/arm["arm"]
    if folder.exists():raise FileExistsError(f"first {split}/{arm['arm']} already started")
    folder.mkdir(parents=True)
    write_once(folder/"attempt.json",{"arm":arm,"config_content_sha256":canonical_hash(arm),
              "started_at_utc":datetime.now(timezone.utc).isoformat(),"routing_source_hashes":routing_sources()})
    items=[q for q in bundle["routing"]["items"] if q["split"]==split]
    if selected_ids is not None:items=[q for q in items if q["id"] in selected_ids]
    cases=[]
    logger.remove()
    try:
        for index,item in enumerate(items,1):
            case=await one_case(item,arm,runtime,run_dir);cases.append(case)
            write_once(folder/"cases"/f"{item['id']}.json",case)
            print(json.dumps({"arm":arm["arm"],"split":split,"progress":f"{index}/{len(items)}",
               "id":case["id"],"confusion":case["confusion"],"tools":[c["name"] for c in case["tool_calls"]],
               "seconds":round(case["latency_ms"]/1000,1),"error":case["error"]},ensure_ascii=False),flush=True)
    finally:
        if getattr(runtime.provider,"_client",None):await runtime.provider._client.close()
    summary=summarize(cases)
    write_once(folder/"summary.json",summary)
    verify_run(run_dir)
    print(json.dumps({"arm":arm["arm"],"split":split,"metrics":summary["metrics"]},ensure_ascii=False),flush=True)
    return summary

def load_cases(run_dir,split,name):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run_dir/split/name/"cases").glob("*.json"))]

def freeze_config(run_dir,config_path=CONFIG_PATH):
    from .config import choose_arm
    verify_run(run_dir)
    candidates={}
    for name in ("A0","A1","A2"):
        data=json.loads((run_dir/"dev"/name/"summary.json").read_text(encoding="utf-8"))
        attempt=json.loads((run_dir/"dev"/name/"attempt.json").read_text(encoding="utf-8"))
        if data["metrics"]["total"]!=30:raise ValueError("dev incomplete")
        candidates[name]={"metrics":data["metrics"],"config":attempt["arm"]}
    selected=choose_arm(candidates)
    registry=discover_tool(run_dir/"plugin_rag_config.json",candidates[selected]["config"]["tool_description"])
    schema=registry.get_definitions()[0]
    body={"experiment_version":"v0.2-routing-1","selected_arm":selected,"selected_config":candidates[selected]["config"],
          "baseline_config":candidates["A0"]["config"],"selection_policy":SELECTION_POLICY,
          "dev_metrics":{n:c["metrics"] for n,c in candidates.items()},
          "tool_schema":schema,"tool_schema_sha256":canonical_hash(schema),
          "tool_parameters_sha256":canonical_hash(schema["function"]["parameters"]),
          "dataset_manifest_sha256":digest(ROOT/"eval/v0.2/freeze_manifest.json"),"few_shot":[],
          "locked_at_utc":datetime.now(timezone.utc).isoformat(),"source_hashes":routing_sources()}
    # 内部hash排除自身字段；另记录实际文件byte hash。
    body["config_hash"]=canonical_hash(body)
    write_once(config_path,body)
    write_once(run_dir/"routing_lock.json",{"config_content_sha256":body["config_hash"],
             "config_file_sha256":digest(config_path),"locked_at_utc":body["locked_at_utc"],"source_hashes":routing_sources()})
    print("Selected:",selected,"config hash:",body["config_hash"],flush=True)

async def formal_test(run_dir,config_path=CONFIG_PATH):
    config=json.loads(config_path.read_text(encoding="utf-8"));lock=json.loads((run_dir/"routing_lock.json").read_text(encoding="utf-8"))
    body=dict(config);expected=body.pop("config_hash")
    if canonical_hash(body)!=expected or digest(config_path)!=lock["config_file_sha256"] or routing_sources()!=lock["source_hashes"]:
        raise ValueError("routing configuration/implementation changed since lock")
    verify_run(run_dir)
    if (run_dir/"test").exists():raise FileExistsError("first formal test already started")
    write_once(run_dir/"test/official_attempt.json",{"config_file_sha256":lock["config_file_sha256"],
             "started_at_utc":datetime.now(timezone.utc).isoformat(),"selected_arm":config["selected_arm"],"repeat":1})
    await run_arm(run_dir,"test",config["baseline_config"])
    if config["selected_arm"]!="A0":await run_arm(run_dir,"test",config["selected_config"])
    verify_run(run_dir)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--stage",choices=["init","dev","lock","test"],required=True)
    p.add_argument("--run-dir",required=True);p.add_argument("--arm-file")
    p.add_argument("--config-file",default=str(CONFIG_PATH),help="正式实验默认写实验目录；独立重跑可写新artifacts配置")
    args=p.parse_args();r=Path(args.run_dir).resolve();config_path=Path(args.config_file).resolve()
    if config_path!=CONFIG_PATH.resolve() and not config_path.is_relative_to(ROOT/"artifacts/v0.2/routing"):
        raise ValueError("replay config must be isolated routing artifact")
    if not r.is_relative_to(ROOT/"artifacts/v0.2/routing"):raise ValueError("isolated routing output required")
    if args.stage=="init":initialize(r)
    elif args.stage=="dev":
        arm=baseline() if not args.arm_file else json.loads(Path(args.arm_file).read_text(encoding="utf-8"))
        asyncio.run(run_arm(r,"dev",arm))
    elif args.stage=="lock":freeze_config(r,config_path)
    else:asyncio.run(formal_test(r,config_path))
if __name__=="__main__":main()
