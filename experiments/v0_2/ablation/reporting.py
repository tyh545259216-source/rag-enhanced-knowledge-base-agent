"""聚合已冻结rubric下的匿名正确性和非盲实际证据复核，不覆盖历史结果。"""
import json
from .config import ROOT,CONFIG,write_once
from .runner import verify,cases,digest
from .evaluate import validate_judgment,summarize,coverage,evidence
from experiments.v0_2.datasets import load_bundle

def generate(run_dir):
    cfg=verify(run_dir);rows=cases(run_dir);gold={i['id']:i for i in load_bundle(ROOT)['routing']['items']}
    mapping=json.loads((run_dir/'judgment_mapping.json').read_text(encoding='utf-8'));blind=json.loads((run_dir/'judgments.json').read_text(encoding='utf-8'));g=json.loads((run_dir/'grounding_review.json').read_text(encoding='utf-8'))
    if set(blind)!=set(mapping):raise ValueError('all anonymous candidates must be judged once')
    judged={s:{} for s in ['B0','B1','B2']}
    for key,j in blind.items():
        m=mapping[key];validate_judgment(j,gold[m['id']]);judged[m['strategy']][m['id']]=j
    for s in judged:
        if set(g[s])!=set(judged[s]):raise ValueError('grounding review must cover all cases')
        if any(v.get('provided_evidence_grounded') not in ['yes','no'] or not v.get('reason') for v in g[s].values()):raise ValueError('explicit grounding decision required')
    by={s:[c for c in rows if c['strategy']==s] for s in judged};summary={s:summarize(by[s],judged[s],g[s],gold) for s in judged}
    good=lambda s,i:judged[s][i]['correctness'] in ['correct','correct_abstention'];ids=sorted(gold_id for gold_id in judged['B2'])
    bad={'B0_wrong_B1_B2_correct':[i for i in ids if not good('B0',i) and good('B1',i) and good('B2',i)],'B1_wrong_B2_correct':[i for i in ids if not good('B1',i) and good('B2',i)],'B2_wrong_B1_correct':[i for i in ids if not good('B2',i) and good('B1',i)],'all_wrong':[i for i in ids if not any(good(s,i) for s in judged)],'B2_routing_correct_answer_wrong':[i for i in ids if not good('B2',i)]}
    manifest={p.relative_to(run_dir).as_posix():digest(p) for p in sorted(run_dir.rglob('*.json')) if p.name!='raw_manifest.json'};write_once(run_dir/'raw_manifest.json',manifest)
    result={'experiment':'v0.2-ablation-first','checkpoint':cfg['checkpoint'],'dataset_hash':cfg['dataset_manifest_sha256'],'evaluation_config':cfg,'rubric_hash':cfg['rubric_hash'],'config_hash':cfg['config_hash'],'strategies':summary,'bad_cases':bad,'judgments':judged,'provided_evidence_grounding':g,'limitations':cfg['rubric']['limitations']+[cfg['rubric']['blindness']],'raw_path_label':run_dir.relative_to(ROOT).as_posix(),'raw_manifest':manifest,'raw_manifest_hash':digest(run_dir/'raw_manifest.json'),'B2_original_manifest_hash':digest(ROOT/'artifacts/v0.2/routing/phase3_first_20261005/raw_manifest.json')}
    lines=['# V0.2 Phase 3B — Agentic RAG Ablation','','## Protocol','','B0禁用工具；B1固定策略调度真实ToolRegistry/execute_tool_calls后，role=tool交给AgentRunner单次Qwen生成；B2复用Phase3A首次A2。B1的assistant tool_calls是明确策略安排，不是Qwen输出，也不用于证明structured tool calling。',
    '三者冻结A2 system与generation不变。B1原query检索，top_k匹配A2同题实际值；原未检索5题用schema默认3。B1没有规划LLM、生成后不重新检索；B2通常两次LLM。B1/B2的query、上下文/调用数和测量时间不同，不能将差异全归为routing。',
    '先冻结rubric，再运行B0/B1。strict=(correct+correct_abstention)/20；partial不计strict分。错误附加私有事实判incorrect。B0私有漏检索是strategy-imposed；B1多余检索不是工具错误。',
    'Grounded采用实际收到的证据复核，reference-grounded另存；Evidence completeness为required chunks实际覆盖，不是答案是否提到所有事实。no-answer无required chunks记not_applicable。',
    '', '## Configuration', '',f"Rubric hash: `{cfg['rubric_hash']}`；config hash: `{cfg['config_hash']}`。"]
    for s,a in summary.items():
        lines+=['','## '+s,'',f"Strict final: {a['strict_correct']}/{a['total']} ({a['strict_accuracy']:.2%}); counts: {json.dumps(a['counts'])}"]
        lines+=['- '+cat+f": {m['correct']}/{m['total']}" for cat,m in a['categories'].items()]
        lines+=[f"- Tool usage: {json.dumps(a['tool_usage'])}",f"- Grounded: {a['grounded']}/{a['total']}; unsupported private claim cases: {a['unsupported_private_claim_cases']}",f"- Evidence completeness: {json.dumps(a['evidence_completeness'])}",f"- No-answer abstention: {a['no_answer']['correct_abstention']}/{a['no_answer']['total']}",f"- Multi-evidence complete: {a['multi_evidence']['complete_evidence']}/{a['multi_evidence']['total']}; fully correct answer: {a['multi_evidence']['fully_correct']}/{a['multi_evidence']['total']}"]
        for label,d in a['latency'].items():
            lines+=['- '+label+(': not_applicable' if d is None else f": n={d['n']}, mean={d['mean']:.2f}, median={d['median']:.2f}, p95={d['p95']:.2f} ms")]
        lines+=[f"- Model errors: {a['model_errors']}; actual LLM request count: {a['llm_request_count']}"]
    lines+=['','## Paired Bad Cases','']+['- '+k+': '+', '.join(v) for k,v in bad.items()]
    representatives=set(i for values in bad.values() for i in values[:1])|{'v2-a-005','v2-a-023','v2-a-048','v2-a-049'}
    for ident in sorted(representatives):
        lines+=['','### '+ident,'', '- Input: '+gold[ident]['query'],'- Expected: '+gold[ident]['expected_answer']]
        for s in judged:
            c=next(c for c in by[s] if c['id']==ident);lines+=['- '+s+' '+judged[s][ident]['correctness']+': '+str(c['final_response']),'- Engineering reason: '+judged[s][ident]['reason'],'- Actual evidence IDs: '+', '.join(t['chunk_id'] for t in evidence(c))]
    lines+=['','## Limitations','']+['- '+x for x in result['limitations']]
    lines+=['','本地Qwen推理主导耗时；检索通常百毫秒级，实际耗时以首轮记录为准。这不是production latency benchmark。每类4题，1题即25个百分点。B2 route 20/20不等于final answer 20/20。',
      '', '## Reproduction', '', '```powershell','python scripts/v0_2/run_ablation.py --stage init --run-dir artifacts/v0.2/ablation/<first-run>','python scripts/v0_2/run_ablation.py --stage run --strategy B0 --run-dir artifacts/v0.2/ablation/<first-run>','python scripts/v0_2/run_ablation.py --stage run --strategy B1 --run-dir artifacts/v0.2/ablation/<first-run>','python scripts/v0_2/run_ablation.py --stage judge-input --run-dir artifacts/v0.2/ablation/<first-run>','# 按固定rubric保存judgments.json与grounding_review.json，禁止看结果调rubric。','python scripts/v0_2/run_ablation.py --stage report --run-dir artifacts/v0.2/ablation/<first-run>','```','EVAL_CONFIG只写一次；新run-dir可复用该冻结配置但拒绝任何source/rubric/config差异；本次首次目录不可覆盖。独立复现使用全新的artifacts路径，原文件保持不变。B2需要ignored Phase3A原trace、Phase2索引，本快照不能代替raw trace。']
    write_once(ROOT/'docs/v0.2/evidence/PHASE3_ABLATION.json',result)
    with (ROOT/'docs/v0.2/ABLATION_REPORT.md').open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(lines)+'\n')
