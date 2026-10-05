"""消融口径与真实executor协议单元测试；假工具仅用于单元测试，非模型成功证据。"""
import asyncio,json
from copy import deepcopy
import pytest
from nanobot.agent.tools.base import Tool,ToolResult
from nanobot.agent.tools.registry import ToolRegistry
from experiments.v0_2.ablation.config import forced_args,RUBRIC
from experiments.v0_2.ablation.evaluate import coverage,validate_judgment,summarize
from experiments.v0_2.ablation.runner import execute_forced,run
from experiments.v0_2.routing.config import write_once

@pytest.mark.parametrize('k',[1,2,3,5,10])
def test_matched_top_k(k):
    assert forced_args({'query':'原问题'},{'tool_calls':[{'arguments':{'top_k':k,'query':'改写'}}]})=={'query':'原问题','top_k':k}
def test_default_k_for_no_tool():assert forced_args({'query':'通用问题'},{'tool_calls':[]})['top_k']==3
@pytest.mark.parametrize('k',[0,11,True,'3'])
def test_bad_matched_k(k):
    with pytest.raises(ValueError):forced_args({'query':'q'},{'tool_calls':[{'arguments':{'top_k':k}}]})
def test_stop_on_multiple_original_calls():
    with pytest.raises(ValueError):forced_args({'query':'q'},{'tool_calls':[{},{}]})
@pytest.mark.parametrize('required,found,expected',[([],[],'not_applicable'),(['a'],[],'none'),(['a','b'],['a'],'partial'),(['a','b'],['a','b','x'],'complete')])
def test_actual_evidence_coverage(required,found,expected):
    row={'tool_results':[{'content':json.dumps({'results':[{'chunk_id':x} for x in found]})}]}
    assert coverage(row,{'expected_chunk_ids':required})==expected

def judgment(kind='correct',unsupported=False):return dict(correctness=kind,reference_grounded='yes',answer_fact_completeness='complete',unsupported_private_claim=unsupported,reason='explicit engineering reason')
@pytest.mark.parametrize('category,kind,valid',[('general_no_tool','correct',True),('private_single_fact','partial',True),('private_no_answer','correct_abstention',True),('private_no_answer','correct',False),('private_single_fact','correct_abstention',False)])
def test_abstention_scope(category,kind,valid):
    if valid:validate_judgment(judgment(kind),{'category':category})
    else:
        with pytest.raises(ValueError):validate_judgment(judgment(kind),{'category':category})
@pytest.mark.parametrize('kind',['correct','partial','correct_abstention'])
def test_unsupported_claim_cannot_get_credit(kind):
    with pytest.raises(ValueError):validate_judgment(judgment(kind,True),{'category':'private_no_answer' if kind=='correct_abstention' else 'private_single_fact'})
def test_b2_no_execution():
    with pytest.raises(ValueError,match='never'):asyncio.run(run(None,'B2'))
def test_write_once_does_not_overwrite(tmp_path):
    p=tmp_path/'case.json';write_once(p,{'first':True})
    with pytest.raises(FileExistsError):write_once(p,{'first':False})
    assert json.loads(p.read_text())=={'first':True}

def test_counts_partial_excluded_and_denominators():
    categories=['general_no_tool','private_single_fact','private_multi_evidence','private_no_answer'];kinds=['correct','incorrect','partial','correct_abstention']
    gold={str(i):dict(category=cat,expected_tool=None if i==0 else 'search_knowledge_base',expected_chunk_ids=['a','b'] if i==2 else []) for i,cat in enumerate(categories)}
    rows=[dict(id=str(i),strategy='B0',tool_results=[],latency_ms=1,requests=[],error=None) for i in range(4)]
    j={str(i):judgment(kind) for i,kind in enumerate(kinds)};g={str(i):{'provided_evidence_grounded':'yes'} for i in range(4)}
    s=summarize(rows,j,g,gold)
    assert s['strict_correct']==2 and s['strict_accuracy']==.5 and s['counts']['partial']==1
    assert s['tool_usage']['missed']==3 and s['tool_usage']['missed_denominator']==3
    assert s['tool_usage']['unnecessary_denominator']==1 and s['multi_evidence']['complete_evidence']==0
    assert s['no_answer']=={'correct_abstention':1,'total':1}

class ReadonlyFake(Tool):
    name='search_knowledge_base';description='unit-only';read_only=True;parameters={'type':'object','properties':{'query':{'type':'string'},'top_k':{'type':'integer'}},'required':['query']}
    async def execute(self,query,top_k):return ToolResult(json.dumps({'results':[{'chunk_id':'a','text':query}]}))
def test_forced_call_uses_executor_and_pairs_tool_message():
    registry=ToolRegistry();registry.register(ReadonlyFake());case=dict(requests=[],tool_calls=[],tool_results=[])
    cfg={'b1_arguments':{'q':{'query':'real argument','top_k':3}},'generation_and_context':{'max_tool_result_chars':12000}}
    msgs=asyncio.run(execute_forced(case,{'id':'q'},cfg,registry,[{'role':'user','content':'question'}]))
    assert [m['role'] for m in msgs]==['user','assistant','tool']
    assert msgs[-1]['tool_call_id']==msgs[-2]['tool_calls'][0]['id']
    assert msgs[-1]['content']==case['tool_results'][0]['content']
    assert case['tool_calls'][0]['native_structured'] is False
    assert 'strategy-imposed' in case['tool_calls'][0]['origin']
