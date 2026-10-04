"""离线评估；原句检索对照仅在 Agent 实验全部完成后运行，不参与模型路由。"""
import json,statistics,hashlib
from pathlib import Path
from dataclasses import asdict
from collections import Counter
from knowledge_base_agent.rag.config import load_config
from knowledge_base_agent.rag.adapter import RAGAdapter
from knowledge_base_agent.rag.retriever import Retriever
from knowledge_base_agent.tools.search_knowledge_base import SearchKnowledgeBaseTool
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"phase3b"

def routing_metrics(cases):
    counts=dict(TP=0,FP=0,FN=0,TN=0)
    for c in cases:
        expected=c['expected_tool']=='search_knowledge_base'
        actual='search_knowledge_base' in c['actual_tools']
        counts['TP' if expected and actual else 'FN' if expected else 'FP' if actual else 'TN']+=1
    tp,fp,fn,tn=(counts[k] for k in ['TP','FP','FN','TN'])
    precision=tp/(tp+fp) if tp+fp else 0
    recall=tp/(tp+fn) if tp+fn else 0
    return {**counts,'accuracy':(tp+tn)/len(cases) if cases else None,'precision':precision,'recall':recall,
            'f1':2*precision*recall/(precision+recall) if precision+recall else 0}

def distribution(values):
    if not values:return None
    values=sorted(values);pos=.95*(len(values)-1);lo=int(pos);hi=min(lo+1,len(values)-1)
    return {'n':len(values),'mean':statistics.mean(values),'median':statistics.median(values),
            'p95':values[lo]+(values[hi]-values[lo])*(pos-lo)}

def main():
    trace=json.loads((OUT/'trace.json').read_text(encoding='utf-8'))
    dataset=json.loads((ROOT/'eval/agent_routing_golden.json').read_text(encoding='utf-8'))
    assert len(trace['cases'])==len(dataset['items'])==24
    judgments=json.loads((OUT/'manual_judgments.json').read_text(encoding='utf-8'))
    adapter=RAGAdapter(load_config(ROOT/'config.yaml'));assert adapter.load()
    retriever=Retriever(adapter);tool=SearchKnowledgeBaseTool();details=[]
    for case in trace['cases']:
        judge=judgments[case['id']]
        detail={'id':case['id'],'category':case['category'],'question':case['question'],'expected_tool':case['expected_tool'],
                'actual_tools':case['actual_tools'],'final_answer':case.get('final_answer'),**judge}
        calls=case['tool_calls'];events=case['tool_results'];reference=[]
        relevant=set(case['expected_evidence']);found=set();args=[]
        for call in calls:
            parameters=call['arguments'];valid=call['native_structured'] and not tool.validate_params(parameters) and bool(str(parameters.get('query','')).strip())
            event=next((e for e in events if e['tool_call_id']==call['id']),None)
            actual=json.loads(event['content']).get('results',[]) if event and not event['is_error'] else []
            found.update(x['chunk_id'] for x in actual)
            if valid:
                k=parameters.get('top_k',3)
                # 原句对照不影响 Agent：只是离线测量同一 Retriever 的 query 改写效果。
                reference=[dict(rank=i,**asdict(x)) for i,x in enumerate(retriever.search(case['question'],k),1)]
            reference_ids={x['chunk_id'] for x in reference};actual_ids={x['chunk_id'] for x in actual}
            if relevant:
                old=len(reference_ids&relevant)/len(relevant);new=len(actual_ids&relevant)/len(relevant)
                effect='improved' if new>old else 'degraded' if new<old else 'preserved'
            else:
                old=new=None
                effect='preserved_no_answer_status' if case['category']=='private_no_answer' else 'not_applicable'
            args.append({'tool_call_id':call['id'],'valid':valid,'original_query':case['question'],
                         'rewritten_query':parameters.get('query'),'rewritten':parameters.get('query')!=case['question'],
                         'top_k':parameters.get('top_k',3),'intent_preserved':judge.get('intent_preserved'),
                         'reference_results':reference,'actual_results':actual,'retrieval_effect':effect,
                         'reference_evidence_recall':old,'actual_evidence_recall':new,
                         'same_ranking':[x['chunk_id'] for x in reference]==[x['chunk_id'] for x in actual]})
        detail['arguments']=args
        detail['routing_correct']=(bool(calls and 'search_knowledge_base' in case['actual_tools']))==bool(case['expected_tool'])
        detail['evidence_recall']=len(found&relevant)/len(relevant) if relevant else None
        detail['evidence_complete']=relevant<=found if relevant else None
        details.append(detail)
    all_args=[a for d in details for a in d['arguments']]
    private=[d for d in details if d['expected_tool']];answerable= [d for d in details if d['category'] in ['private_single_fact','private_multi_evidence']]
    noanswer=[d for d in details if d['category']=='private_no_answer']
    groups={}
    for category in sorted({d['category'] for d in details}):
        cases=[c for c in trace['cases'] if c['category']==category]
        groups[category]=routing_metrics(cases)
    latency={}
    for name,called in [('no_tool',False),('tool_call',True)]:
        selected=[c for c in trace['cases'] if bool(c['tool_calls'])==called]
        latency[name]={'e2e_ms':distribution([c['total_latency_ms'] for c in selected])}
        if called:
            latency[name].update({'llm1_ms':distribution([c['requests'][0]['latency_ms'] for c in selected if c['requests'][0].get('latency_ms') is not None]),
                'retrieval_ms':distribution([sum(x['latency_ms'] for x in c['tool_results']) for c in selected]),
                'llm2_ms':distribution([c['requests'][1]['latency_ms'] for c in selected if len(c['requests'])>1 and c['requests'][1].get('latency_ms') is not None])})
    result={'routing':routing_metrics(trace['cases']),'categories':groups,'tool_argument_valid_count':sum(a['valid'] for a in all_args),'tool_argument_count':len(all_args),
            'rewrite_count':sum(a['rewritten'] for a in all_args),'rewrite_effects':dict(Counter(a['retrieval_effect'] for a in all_args if a['rewritten'])),
            'answerable_evidence_complete_count':sum(d['evidence_complete'] for d in answerable),'answerable_count':len(answerable),
            'private_grounded_count':sum(d['grounded'] for d in private),'private_correct_count':sum(d['answer_correct'] for d in private),'private_count':len(private),
            'no_answer_count':len(noanswer),'no_answer_abstained_count':sum(d['abstained'] for d in noanswer),
            'no_answer_hallucination_count':sum(d['hallucinated'] for d in noanswer),
            'no_answer_tool_and_abstained_count':sum(d['routing_correct'] and d['abstained'] for d in noanswer),
            'all_private_hallucination_count':sum(d['hallucinated'] for d in private),'latency':latency,'details':details,
            'limitations':'单次24题，只开放一个知识库工具；每类6题，人工按冻结资料标注和判读，不代表多工具场景或生产可靠性。无答案效果不以分数或空集合Recall判断。'}
    (OUT/'evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['details']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
