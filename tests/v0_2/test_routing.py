"""路由实验统计与观测测试；模拟HTTP只用于测试观测器，不作为模型成功证据。"""
import asyncio,json,os,time
from copy import deepcopy
import httpx,pytest
from experiments.v0_2.routing.config import *
from experiments.v0_2.routing.evaluate import confusion,routing_metrics,argument_valid,summarize
from experiments.v0_2.routing.observe import DescriptionTool,ObservedStream
from experiments.v0_2.routing.runner import temporary_kb_config
from nanobot.agent.tools.base import Tool,ToolResult

@pytest.mark.parametrize("expected,actual,label",[(True,True,"TP"),(True,False,"FN"),(False,True,"FP"),(False,False,"TN")])
def test_confusion(expected,actual,label):assert confusion(expected,actual)==label

def test_metrics_denominators():
    rows=[dict(expected_use_tool=e,actual_use_tool=a) for e,a in [(True,True),(True,True),(True,False),(False,True),(False,False)]]
    m=routing_metrics(rows)
    assert m['accuracy']==.6 and m['precision']==pytest.approx(2/3) and m['recall']==pytest.approx(2/3)
    assert m['f1']==pytest.approx(2/3)

def test_empty_metrics():
    assert routing_metrics([])['accuracy'] is None
    assert routing_metrics([])['f1']==0

@pytest.mark.parametrize('args,valid',[(dict(query='资料'),True),(dict(query='资料',top_k=10),True),(dict(query=' '),False),(dict(query='a',top_k=0),False),(dict(query='a',top_k=11),False),(dict(query='a',top_k=True),False),(dict(query='a',top_k='3'),False),(dict(query='a',extra=1),False),({},False),(None,False)])
def test_argument_contract(args,valid):assert bool(argument_valid(dict(name=TOOL,arguments=args)))==valid

def test_wrong_tool():assert not argument_valid(dict(name='exec',arguments=dict(query='a')))

@pytest.mark.parametrize('key,value',[("temperature",.2),("model","another"),("max_iterations",5),("few_shot",['example'])])
def test_runtime_frozen(key,value):
    a=baseline();a[key]=value
    with pytest.raises(ValueError):validate_arm(a)

def test_a1_description_only():
    a=baseline();a.update(arm='A1',tool_description=DESCRIPTION_V1)
    assert validate_arm(a)==a
    a['system_instruction']='changed'
    with pytest.raises(ValueError):validate_arm(a)

def test_selection_precision_guard_and_simplicity():
    def arm(name,tp,fp,fn,tn):
        rows=[dict(expected_use_tool=e,actual_use_tool=a) for e,a,n in [(True,True,tp),(False,True,fp),(True,False,fn),(False,False,tn)] for _ in range(n)]
        c=baseline();c['arm']=name;c['tool_description']+=' longer' if name!='A0' else ''
        return dict(metrics=routing_metrics(rows),config=c)
    arms={'A0':arm('A0',10,0,5,5),'A1':arm('A1',15,2,0,3),'A2':arm('A2',14,0,1,5)}
    assert choose_arm(arms)=='A2'
    arms['A2']=arm('A2',10,0,5,5)
    assert choose_arm(arms)=='A0'

def test_hash_order_independent():assert canonical_hash({'a':1,'b':2})==canonical_hash({'b':2,'a':1})

def test_write_once_retains_original(tmp_path):
    p=tmp_path/'a.json';write_once(p,{'first':1})
    with pytest.raises(FileExistsError):write_once(p,{'second':2})
    assert json.loads(p.read_text())=={'first':1}

def test_process_env_restored(monkeypatch):
    monkeypatch.setenv('KNOWLEDGE_BASE_CONFIG','original')
    with temporary_kb_config('experiment'):assert os.environ['KNOWLEDGE_BASE_CONFIG']=='experiment'
    assert os.environ['KNOWLEDGE_BASE_CONFIG']=='original'
    monkeypatch.delenv('KNOWLEDGE_BASE_CONFIG')
    with temporary_kb_config('experiment'):pass
    assert 'KNOWLEDGE_BASE_CONFIG' not in os.environ

class Dummy(Tool):
    name='search_knowledge_base';description='original';parameters={'type':'object'};read_only=True;concurrency_safe=False
    async def execute(self,**params):self.args=params;return ToolResult('original result')

def test_description_wrapper_delegates():
    t=Dummy();wrapped=DescriptionTool(t,'candidate')
    assert wrapped.parameters is t.parameters and wrapped.name==t.name and wrapped.read_only
    assert asyncio.run(wrapped.execute(query='unchanged'))=='original result'
    assert t.args=={'query':'unchanged'} and t.description=='original'

def test_sse_observation_preserves_bytes():
    payload={'choices':[{'delta':{'content':'中文','tool_calls':[{'index':0,'id':'call_1'}]},'finish_reason':'tool_calls'}]}
    raw=('data: '+json.dumps(payload,ensure_ascii=False)+'\n\ndata: [DONE]\n\n').encode()
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for b in raw:yield bytes([b])
    record=dict(raw_tool_call_deltas=[],wire_content='')
    async def collect():return b''.join([b async for b in ObservedStream(Stream(),record,time.perf_counter())])
    assert asyncio.run(collect())==raw
    assert record['wire_content']=='中文' and record['finish_reason']=='tool_calls'
    assert record['raw_tool_call_deltas']==[{'index':0,'id':'call_1'}]

def test_failed_case_not_dropped():
    c=dict(id='failed',category='private',expected_use_tool=True,actual_use_tool=False,confusion='FN',latency_ms=10,requests=[],tool_calls=[],tool_results=[],error='timeout')
    s=summarize([c]);assert s['metrics']['FN']==1 and s['model_errors']==['failed']

def test_sse_finish_timing_available_before_exhaustion(monkeypatch):
    from experiments.v0_2.routing import observe
    monkeypatch.setattr(observe.time,'perf_counter',lambda:2.)
    raw=b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):yield raw
    record=dict(raw_tool_call_deltas=[],wire_content='')
    async def inspect_first():
        stream=ObservedStream(Stream(),record,1.);iterator=stream.__aiter__()
        await iterator.__anext__()
        assert record['latency_ms']==1000
        monkeypatch.setattr(observe.time,'perf_counter',lambda:99.)
        await iterator.aclose();await stream.aclose()
        assert record['latency_ms']==1000
    asyncio.run(inspect_first())

def test_http_observer_does_not_store_headers(monkeypatch):
    from experiments.v0_2.routing.observe import observe_http
    async def original(client,request,**kwargs):return httpx.Response(200,content=b'')
    monkeypatch.setattr(httpx.AsyncClient,'send',original)
    case=dict(requests=[])
    async def run():
        async with httpx.AsyncClient() as c:
            req=httpx.Request('POST','http://localhost:11434/v1/chat/completions',headers={'Authorization':'never-record-this','Cookie':'never-record-cookie'},json={'model':'qwen3:1.7b','messages':[]})
            with observe_http(case,baseline()):await c.send(req)
    asyncio.run(run())
    assert httpx.AsyncClient.send is original
    assert 'never-record' not in json.dumps(case) and case['requests'][0]['http_status']==200

def test_manual_review_exact_coverage():
    from experiments.v0_2.routing.reporting import review_calls
    cases=[{'id':'a','tool_calls':[{}]}]
    good=[{'id':'a','call_index':0,'intent_preserved':True,'reason':'equivalent private intent'}]
    assert review_calls(cases,good)['rate']==1
    for wrong in [[],good+good,[dict(good[0],intent_preserved='yes')]]:
        with pytest.raises(ValueError):review_calls(cases,wrong)

def test_metric_render_counts_not_only_percentages():
    from experiments.v0_2.routing.reporting import metric_line
    m=routing_metrics([dict(expected_use_tool=True,actual_use_tool=False)])
    text=metric_line(m);assert 'FN=1' in text and 'Recall=0.0000%' in text

def test_summary_audit_does_not_mask_metric_changes():
    from experiments.v0_2.routing.reporting import audit_summary
    raw={'metrics':{'FN':5},'latency':{'tool':{'llm2_ms':None}}}
    saved=deepcopy(raw);saved['latency']['tool']['llm2_ms']={'n':16}
    assert audit_summary(raw,saved,'dev/A0')
    with pytest.raises(ValueError):audit_summary(raw,saved,'test/A0')
    saved['metrics']['FN']=4
    with pytest.raises(ValueError):audit_summary(raw,saved,'dev/A0')

def test_request_audit_checks_scope_and_transport():
    from experiments.v0_2.routing.reporting import audit_requests
    arm=baseline();params={'type':'object'}
    schema={'function':{'name':TOOL,'description':arm['tool_description'],'parameters':params}}
    messages=[{'role':'system','content':arm['system_instruction']},{'role':'user','content':'query'}]
    req={'model':arm['model'],'endpoint':arm['endpoint'],'generation':{k:arm[k] for k in ['temperature','max_tokens','reasoning_effort']},'tools':[schema],'messages':messages}
    row={'query':'query','tool_calls':[{'id':'c1'}],'tool_results':[{'tool_call_id':'c1'}],'requests':[req,dict(req,messages=messages+[{'role':'assistant','tool_calls':[{'id':'c1'}]},{'role':'tool','tool_call_id':'c1'}])]}
    assert audit_requests([row],arm,canonical_hash(params))['role_tool_ids_verified']==1
    for field,value in [('model','wrong'),('tool_choice','required')]:
        broken=deepcopy(row);broken['requests'][0][field]=value
        with pytest.raises(ValueError):audit_requests([broken],arm,canonical_hash(params))
    broken=deepcopy(row);broken['requests'][1]['messages'][-1]['tool_call_id']='wrong'
    with pytest.raises(ValueError):audit_requests([broken],arm,canonical_hash(params))
