"""B0/B1真实运行，B2仅复制派生已有trace；逐题只写一次、支持missing-ID恢复。"""
import argparse,asyncio,json,sys,time,traceback,subprocess
from datetime import datetime,timezone
from pathlib import Path
from loguru import logger
from nanobot.agent.runner import AgentRunner,AgentRunSpec
from nanobot.agent.hook import AgentHookContext
from nanobot.agent.tools.execution import execute_tool_calls
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.providers.base import ToolCallRequest
from nanobot.utils.helpers import build_assistant_message
from experiments.v0_2.datasets import load_bundle
from experiments.v0_2.retrieval.runner import verify_integrity,protected_hashes,digest
from experiments.v0_2.routing.runner import make_runtime,discover_tool,no_compaction
from experiments.v0_2.routing.observe import ObserveHook,observe_http
from .config import ROOT,CONFIG,RUBRIC,canonical_hash,write_once,forced_args
ROUTING=ROOT/'artifacts/v0.2/routing/phase3_first_20261005'
PHASE2=ROOT/'artifacts/v0.2/retrieval/phase2_first_20261005'
def sources():
    paths=list((ROOT/'experiments/v0_2/ablation').glob('*.py'))+[ROOT/'scripts/v0_2/run_ablation.py',ROOT/'tests/v0_2/test_ablation.py']
    return {p.relative_to(ROOT).as_posix():digest(p) for p in sorted(paths)}
def b2_cases():
    return {p.stem:json.loads(p.read_text(encoding='utf-8')) for p in (ROUTING/'test/A2/cases').glob('*.json')}
def verify(run_dir):
    lock=json.loads((run_dir/'lock.json').read_text(encoding='utf-8'))
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'));body=dict(cfg);h=body.pop('config_hash')
    if canonical_hash(body)!=h or digest(CONFIG)!=lock['config_file_sha256'] or sources()!=lock['source_hashes']:raise ValueError('ablation config/source changed after lock')
    verify_integrity(lock['protected_files'])
    for folder,values in [('routing',lock['routing_raw_files']),('retrieval',lock['phase2_raw_files'])]:
        base=ROUTING if folder=='routing' else PHASE2
        for p,v in values.items():
            if digest(base/p)!=v:raise ValueError('frozen raw changed: '+p)
    return cfg

def initialize(run_dir):
    if run_dir.exists():raise FileExistsError('new isolated run directory required')
    if subprocess.run(['git','merge-base','--is-ancestor','93293f54be1d62446123eba977c5ece2703a4552','HEAD']).returncode:raise ValueError('required checkpoint missing')
    bundle,protected=verify_integrity();items=[i for i in bundle['routing']['items'] if i['split']=='test'];b2=b2_cases()
    if len(items)!=20 or set(b2)!={i['id'] for i in items}:raise ValueError('incomplete B2/test')
    make_runtime() # 只验证已保存Provider/model/generation，不发模型请求。
    a2=json.loads((ROOT/'experiments/v0_2/routing/ROUTING_CONFIG.json').read_text(encoding='utf-8'))
    lock3=json.loads((ROUTING/'routing_lock.json').read_text(encoding='utf-8'))
    if digest(ROOT/'experiments/v0_2/routing/ROUTING_CONFIG.json')!=lock3['config_file_sha256']:raise ValueError('A2 changed')
    cfg={'experiment':'v0.2-ablation-first','created_at_utc':datetime.now(timezone.utc).isoformat(),'checkpoint':'93293f54be1d62446123eba977c5ece2703a4552','dataset_manifest_sha256':digest(ROOT/'eval/v0.2/freeze_manifest.json'),'rubric':RUBRIC,'rubric_hash':canonical_hash(RUBRIC),'generation_and_context':a2['selected_config'],'A2_config_sha256':lock3['config_file_sha256'],'tool_schema':a2['tool_schema'],
      'strategies':{'B0':'same frozen A2 system + generation; no tools; AgentRunner direct; private misses strategy-imposed','B1':'fixed schedule original query -> real ToolRegistry/execute_tool_calls -> assistant strategy-call + role=tool -> AgentRunner final generation with no replanning tools; no planning LLM; not model-generated tool call','B2':'reuse original A2 first official 20 traces; no model or retrieval rerun'},
      'b1_arguments':{i['id']:forced_args(i,b2[i['id']]) for i in items},'formal_repeats':1,'order':['B0','B1'],'context_reset':True,'source_hashes':sources()}
    cfg['config_hash']=canonical_hash(cfg)
    if CONFIG.exists():
        prior=json.loads(CONFIG.read_text(encoding='utf-8'));body=dict(prior);h=body.pop('config_hash')
        if canonical_hash(body)!=h:raise ValueError('invalid existing frozen config')
        for key in ['dataset_manifest_sha256','rubric','rubric_hash','generation_and_context','A2_config_sha256','tool_schema','strategies','b1_arguments','source_hashes']:
            if prior[key]!=cfg[key]:raise ValueError('reproduction differs from frozen config: '+key)
        cfg=prior # 新输出目录复用同一冻结配置，不覆写首次配置。
    else:write_once(CONFIG,cfg)
    run_dir.mkdir(parents=True)
    write_once(run_dir/'lock.json',{'config_file_sha256':digest(CONFIG),'config_content_sha256':cfg['config_hash'],'rubric_hash':cfg['rubric_hash'],'locked_at_utc':datetime.now(timezone.utc).isoformat(),'source_hashes':sources(),'protected_files':protected,'routing_raw_files':{p.relative_to(ROUTING).as_posix():digest(p) for p in ROUTING.rglob('*') if p.is_file() and '__pycache__' not in p.parts},'phase2_raw_files':{p.relative_to(PHASE2).as_posix():digest(p) for p in PHASE2.rglob('*') if p.is_file()}})
    write_once(run_dir/'plugin_rag_config.json',json.loads((ROUTING/'plugin_rag_config.json').read_text(encoding='utf-8')))
    # 两run目录位于相同深度；原相对索引路径不变。
    for i in items:
        original=ROUTING/'test/A2/cases'/f"{i['id']}.json"
        c=dict(b2[i['id']]);c['strategy']='B2';c['private']=i['expected_tool'] is not None;c['reuse_provenance']={'source_path':original.relative_to(ROOT).as_posix(),'source_sha256':digest(original),'original_started_at_utc':c['started_at_utc'],'model_reexecuted':False};write_once(run_dir/'B2/cases'/original.name,c)
    verify(run_dir);print('Rubric/config frozen',cfg['rubric_hash'],cfg['config_hash'],flush=True)

async def execute_forced(case,item,cfg,registry,messages):
    call=ToolCallRequest(id='strategy_'+item['id'],name='search_knowledge_base',arguments=cfg['b1_arguments'][item['id']])
    hook=ObserveHook(case);ctx=AgentHookContext(iteration=0,messages=messages,tool_calls=[call]);await hook.before_execute_tools(ctx)
    case['tool_calls'][-1]['origin']='strategy-imposed; not LLM output'
    results,events=await execute_tool_calls(registry,[call],concurrent=False,external_lookup_counts={},workspace_violation_counts={},hook=hook,context=ctx,model_messages=messages)
    payload=str(results[0]);case['strategy_tool_events']=events
    if not case['tool_results']:case['tool_results'].append({'tool_call_id':call.id,'name':call.name,'arguments':call.arguments,'content':payload,'is_error':True,'latency_ms':0})
    if len(payload)>cfg['generation_and_context']['max_tool_result_chars']:raise ValueError('unexpected tool-result truncation requirement')
    return messages+[build_assistant_message(None,[call.to_openai_tool_call()]),{'role':'tool','tool_call_id':call.id,'name':call.name,'content':payload}]

async def one(item,strategy,cfg,runtime,run_dir):
    arm=cfg['generation_and_context'];registry=discover_tool(run_dir/'plugin_rag_config.json',arm['tool_description']) if strategy=='B1' else None
    case={k:item[k] for k in ['id','category','query','split','expected_tool']};case.update(strategy=strategy,private=item['expected_tool'] is not None,expected_use_tool=item['expected_tool'] is not None,requests=[],tool_calls=[],tool_results=[],responses=[],started_at_utc=datetime.now(timezone.utc).isoformat())
    messages=[{'role':'system','content':arm['system_instruction']},{'role':'user','content':item['query']}];start=time.perf_counter()
    try:
        if strategy=='B1':messages=await execute_forced(case,item,cfg,registry,messages)
        case['initial_roles']=[m['role'] for m in messages]
        with observe_http(case,arm):
            result=await asyncio.wait_for(AgentRunner().run(AgentRunSpec(initial_messages=messages,tools=ToolRegistry(),runtime=runtime,max_iterations=arm['max_iterations'],max_tool_result_chars=arm['max_tool_result_chars'],hook=ObserveHook(case),workspace=ROOT,consolidate_history=no_compaction,provider_retry_mode=arm['provider_retry_mode'],finalize_on_max_iterations=arm['finalize_on_max_iterations'])),timeout=arm['case_timeout_seconds'])
        case.update(final_response=result.final_content,error=result.error,stop_reason=result.stop_reason,final_message_roles=[m['role'] for m in result.messages])
    except Exception as exc:case.update(final_response=None,error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()})
    case['latency_ms']=(time.perf_counter()-start)*1000;case['actual_use_tool']=bool(case['tool_results']);case['llm_request_count']=len(case['requests'])
    case['route_interpretation']='strategy-imposed miss' if strategy=='B0' and case['expected_use_tool'] else 'unnecessary retrieval by fixed strategy' if strategy=='B1' and not case['expected_use_tool'] else 'fixed ablation policy, not router prediction'
    return case

async def run(run_dir,strategy,resume=False):
    if strategy not in ['B0','B1']:raise ValueError('B2 must never be executed')
    cfg=verify(run_dir);folder=run_dir/strategy;items=[i for i in load_bundle(ROOT)['routing']['items'] if i['split']=='test']
    if folder.exists() and not resume:raise FileExistsError('first run started; use missing-only resume')
    if resume:
        attempt=json.loads((folder/'attempt.json').read_text(encoding='utf-8'))
        if attempt['config_hash']!=cfg['config_hash']:raise ValueError('resume configuration mismatch')
        present={p.stem for p in (folder/'cases').glob('*.json')}
        if not present<={i['id'] for i in items}:raise ValueError('unexpected IDs')
        write_once(folder/'resume.json',{'resumed_at_utc':datetime.now(timezone.utc).isoformat(),'completed_before_resume':sorted(present),'missing_ids':[i['id'] for i in items if i['id'] not in present],'config_hash':cfg['config_hash']})
        items=[i for i in items if i['id'] not in present]
    else:write_once(folder/'attempt.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),'strategy':strategy,'config_hash':cfg['config_hash'],'rubric_hash':cfg['rubric_hash'],'repeat':1})
    runtime=make_runtime();logger.remove()
    try:
        for idx,item in enumerate(items,1):
            c=await one(item,strategy,cfg,runtime,run_dir);write_once(folder/'cases'/f"{item['id']}.json",c)
            print(json.dumps({'strategy':strategy,'progress':str(idx)+'/'+str(len(items)),'id':item['id'],'calls':len(c['tool_results']),'seconds':round(c['latency_ms']/1000,1),'error':c['error']},ensure_ascii=False),flush=True)
    finally:
        if getattr(runtime.provider,'_client',None):await runtime.provider._client.close()
    verify(run_dir)

def cases(run_dir):
    rows=[]
    for s in ['B0','B1','B2']:
        group=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((run_dir/s/'cases').glob('*.json'))]
        if len(group)!=20 or len({c['id'] for c in group})!=20:raise ValueError('incomplete strategy '+s)
        for c in group:c['strategy']=s
        rows.extend(group)
    return rows

def judgment_input(run_dir):
    verify(run_dir);gold={i['id']:i for i in load_bundle(ROOT)['routing']['items']};chunks={i['chunk_id']:i for i in load_bundle(ROOT)['corpus']['chunks']};mapping={};rows=[]
    for c in cases(run_dir):
        ident=canonical_hash(['ablation-anonymous-1',c['strategy'],c['id']])[:16];mapping[ident]={'strategy':c['strategy'],'id':c['id']}
        g=gold[c['id']];rows.append({'anonymous_id':ident,'query':c['query'],'expected_facts':g['expected_answer'],'gold_evidence':[chunks[x] for x in g['expected_chunk_ids']],'candidate_answer':c['final_response']})
    rows.sort(key=lambda x:x['anonymous_id']);write_once(run_dir/'judgment_input.json',rows);write_once(run_dir/'judgment_mapping.json',mapping)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',choices=['init','run','resume','judge-input','report'],required=True);p.add_argument('--run-dir',required=True);p.add_argument('--strategy',choices=['B0','B1']);a=p.parse_args();r=Path(a.run_dir).resolve()
    if not r.is_relative_to(ROOT/'artifacts/v0.2/ablation'):raise ValueError('isolated ablation output required')
    if a.stage=='init':initialize(r)
    elif a.stage in ['run','resume']:asyncio.run(run(r,a.strategy,a.stage=='resume'))
    elif a.stage=='judge-input':judgment_input(r)
    else:
        from .reporting import generate
        generate(r)
if __name__=='__main__':main()
