"""在固定分母上聚合真实执行和明确工程判定，失败不丢弃。"""
from collections import Counter
from experiments.v0_2.routing.evaluate import distribution
from .config import CLASSES,COMPLETENESS

def evidence(row):
    results=[]
    import json
    for tool in row['tool_results']:
        try:results.extend(json.loads(tool['content']).get('results',[]))
        except (ValueError,TypeError,AttributeError):pass
    return results

def coverage(row,gold):
    required=set(gold['expected_chunk_ids']);found={r['chunk_id'] for r in evidence(row)}
    return 'not_applicable' if not required else 'complete' if required<=found else 'partial' if required&found else 'none'

def validate_judgment(j,gold):
    if j.get('correctness') not in CLASSES or j.get('reference_grounded') not in ['yes','no'] or j.get('answer_fact_completeness') not in COMPLETENESS:raise ValueError('invalid rubric judgment')
    if type(j.get('unsupported_private_claim')) is not bool or not j.get('reason'):raise ValueError('explicit engineering judgment/reason required')
    if j['correctness']=='correct_abstention' and gold['category']!='private_no_answer':raise ValueError('abstention credit only on no-answer')
    if j['correctness']=='correct' and gold['category']=='private_no_answer':raise ValueError('no-answer needs abstention class')
    if j['unsupported_private_claim'] and j['correctness']!='incorrect':raise ValueError('unsupported private claims cannot earn correct/partial')

def summarize(rows,judgments,grounding,gold):
    counts=Counter(judgments[c['id']]['correctness'] for c in rows);n=len(rows);strict=lambda c:judgments[c['id']]['correctness'] in ['correct','correct_abstention']
    positive=[c for c in rows if gold[c['id']]['expected_tool'] is not None];negative=[c for c in rows if gold[c['id']]['expected_tool'] is None]
    used=lambda c:len(c['tool_results'])>0
    noanswer=[c for c in rows if gold[c['id']]['category']=='private_no_answer'];multi=[c for c in rows if gold[c['id']]['category']=='private_multi_evidence']
    status=Counter(coverage(c,gold[c['id']]) for c in rows)
    return {'counts':{k:counts[k] for k in ['correct','partial','incorrect','correct_abstention']},'strict_correct':sum(strict(c) for c in rows),'total':n,'strict_accuracy':sum(strict(c) for c in rows)/n,
     'categories':{cat:{'correct':sum(strict(c) for c in rows if gold[c['id']]['category']==cat),'total':sum(gold[c['id']]['category']==cat for c in rows)} for cat in sorted({gold[c['id']]['category'] for c in rows})},
     'tool_usage':{'called_cases':sum(used(c) for c in rows),'tool_call_rate':sum(used(c) for c in rows)/n,'unnecessary':sum(used(c) for c in negative),'unnecessary_denominator':len(negative),'unnecessary_rate':sum(used(c) for c in negative)/len(negative),'missed':sum(not used(c) for c in positive),'missed_denominator':len(positive),'missed_rate':sum(not used(c) for c in positive)/len(positive),'total_calls':sum(len(c['tool_results']) for c in rows),'average_calls':sum(len(c['tool_results']) for c in rows)/n},
     'grounded':sum(grounding[c['id']]['provided_evidence_grounded']=='yes' for c in rows),'unsupported_private_claim_cases':sum(judgments[c['id']]['unsupported_private_claim'] for c in rows),'evidence_completeness':dict(status),
     'no_answer':{'correct_abstention':sum(judgments[c['id']]['correctness']=='correct_abstention' for c in noanswer),'total':len(noanswer)},'multi_evidence':{'complete_evidence':sum(coverage(c,gold[c['id']])=='complete' for c in multi),'fully_correct':sum(judgments[c['id']]['correctness']=='correct' for c in multi),'total':len(multi)},
     'latency':{'e2e_ms':distribution([c['latency_ms'] for c in rows]),'tool_ms':distribution([sum(t['latency_ms'] for t in c['tool_results']) for c in rows if used(c)]),'llm1_ms':distribution([c['requests'][0]['latency_ms'] for c in rows if c['strategy']=='B2' and used(c) and c['requests'] and c['requests'][0].get('latency_ms') is not None]),'llm_final_ms':distribution([c['requests'][-1]['latency_ms'] for c in rows if c['requests'] and c['requests'][-1].get('latency_ms') is not None])},
     'model_errors':[c['id'] for c in rows if c.get('error')],'llm_request_count':sum(len(c['requests']) for c in rows),'bad_case_ids':[c['id'] for c in rows if not strict(c)]}
