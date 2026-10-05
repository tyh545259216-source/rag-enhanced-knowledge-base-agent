"""由首次trace和明确的人工审阅生成报告；不自动判断LLM内部原因。"""
import argparse,json
from pathlib import Path
from .config import write_once,canonical_hash
from .runner import ROOT,CONFIG_PATH,digest,load_cases,verify_run,routing_sources
from .evaluate import summarize

CAUSES={'ambiguous_query','tool_description_too_narrow','tool_description_too_broad','system_instruction_weak','private_fact_not_recognized','general_question_misclassified','model_capability','other'}

def review_calls(cases,judgments):
    actual={(c['id'],i) for c in cases for i,_ in enumerate(c['tool_calls'])}
    given={(r['id'],r['call_index']) for r in judgments}
    if actual!=given or len(given)!=len(judgments):raise ValueError('manual review must cover each call exactly once')
    if any(type(r.get('intent_preserved')) is not bool or not r.get('reason') for r in judgments):raise ValueError('explicit human intent decision/reason required')
    n=len(actual);good=sum(r['intent_preserved'] for r in judgments)
    return {'method':'coding-assistant engineering trace inspection; semantic judgment, not string equality; no independent human review or separate model-as-judge','intent_preserving':good,'total':n,'rate':good/n if n else None}

def audit_summary(raw,saved,label):
    if raw==saved:return None
    # 已观察到的A0 dev缺口仅允许第二次请求耗时缺失；不能掩盖任何路由/参数/错误差异。
    copy=json.loads(json.dumps(saved))
    if label=='dev/A0' and raw['latency']['tool']['llm2_ms'] is None:
        copy['latency']['tool']['llm2_ms']=None
        if copy==raw:return 'A0 dev LLM2 durations existed in live-memory summary after case serialization, but are absent in persisted case JSON. Raw-based report excludes them; original summary preserved.'
    raise ValueError('summary does not match raw cases')

def audit_requests(cases,arm,schema_hash):
    requests=0;tool_messages=0
    for c in cases:
        expected_ids={t['id'] for t in c['tool_calls']}
        observed_ids=set()
        for i,r in enumerate(c['requests']):
            requests+=1
            if r['model']!=arm['model'] or r['endpoint']!=arm['endpoint']:raise ValueError('model/endpoint differs')
            if any(r['generation'][k]!=arm[k] for k in ('temperature','max_tokens','reasoning_effort')):raise ValueError('generation differs')
            if r.get('tool_choice') not in (None,'auto'):raise ValueError('forced tool selection not allowed')
            if i==0 and r['messages']!=[{'role':'system','content':arm['system_instruction']},{'role':'user','content':c['query']}]:raise ValueError('unexpected model inputs/golden leakage')
            tools=r.get('tools') or []
            if len(tools)!=1 or tools[0]['function']['name']!='search_knowledge_base' or tools[0]['function']['description']!=arm['tool_description']:raise ValueError('tool description differs')
            if canonical_hash(tools[0]['function']['parameters'])!=schema_hash:raise ValueError('tool schema changed')
            assistant_ids={t['id'] for m in r['messages'] if m['role']=='assistant' for t in m.get('tool_calls',[])}
            for m in r['messages']:
                if m['role']=='tool':
                    if m.get('tool_call_id') not in assistant_ids or m.get('tool_call_id') not in expected_ids:raise ValueError('role=tool ID mismatch')
                    observed_ids.add(m['tool_call_id'])
        result_ids={t['tool_call_id'] for t in c['tool_results']}
        if not result_ids<=observed_ids:raise ValueError('executed result absent from subsequent request')
        tool_messages+=len(observed_ids)
    return {'requests_verified':requests,'role_tool_ids_verified':tool_messages,'model_generation_schema_consistent':True,'gold_labels_not_in_model_input':True,'no_manual_tool_choice':True}

def metric_line(m):
    return f"TP={m['TP']}, FP={m['FP']}, FN={m['FN']}, TN={m['TN']}; Accuracy={m['accuracy']:.4%}, Precision={m['precision']:.4%}, Recall={m['recall']:.4%}, F1={m['f1']:.4%}"

def render_report(evidence):
    lines=['# V0.2 Phase 3A — Routing A/B','',
           '这是独立 V0.2 实验。V0.1 结果、Phase2 检索实验和默认 Agent/Tool/Provider 保持不变。',
           '', '## 协议与复现', '',
           '单模型 Qwen3:1.7b、Ollama、本地 HTTP、真实 nanobot AgentRunner、单个只读 search_knowledge_base。每题全新上下文；用 Phase2 的冻结 Dense 索引，未启用 Hybrid。',
           'A0 复用 V0.1 描述与指令；A1 只改通用描述；A2 改描述和通用私有资料指令；无 few-shot、实体白名单或人工指定调用。',
           '先完成 dev30 ×3 arms，按预注册规则选择，再锁定配置。test20 的 A0 与选中方案各运行一次；若选 A0 则只运行一份。失败保留，未挑选重复结果。',
           '', '```powershell',
           'python scripts/v0_2/run_routing.py --stage init --run-dir artifacts/v0.2/routing/<new-run>',
           'python scripts/v0_2/run_routing.py --stage dev --run-dir artifacts/v0.2/routing/<new-run>',
           '# 将证据快照中的 A1/A2 config 保存为 JSON，再分别加 --arm-file 执行 dev。',
           'python scripts/v0_2/run_routing.py --stage lock --run-dir artifacts/v0.2/routing/<new-run> --config-file artifacts/v0.2/routing/<new-run>/routing_config.json',
           'python scripts/v0_2/run_routing.py --stage test --run-dir artifacts/v0.2/routing/<new-run> --config-file artifacts/v0.2/routing/<new-run>/routing_config.json',
           'python scripts/v0_2/report_routing.py --run-dir artifacts/v0.2/routing/<new-run> --config-file artifacts/v0.2/routing/<new-run>/routing_config.json --review-file <manual-review.json> --output-dir artifacts/v0.2/routing/<new-run>/report',
           '```',
           '使用已安装当前项目插件的 nanobot venv。必须先具备冻结的 Phase2 Dense 索引。正式配置只写一次；独立复现实验使用 --config-file 保存新配置到新 artifacts 目录，不能覆盖本次正式配置与证据。',
           '', '## Dev 选择', '']
    for label,a in evidence['dev'].items():lines+=['- '+label+': '+metric_line(a['metrics'])]
    lines+=['',f"选中 **{evidence['selected_arm']}**。只依据 dev，先限制 FP 增量 ≤1、Precision 下降 ≤5 个百分点，再优先 Recall、更少 FP、较短文本。",f"配置内容 hash：`{evidence['config']['config_hash']}`。",'', '## 首次正式 test', '']
    for label,a in evidence['test'].items():
        lines+=['### '+label,'',metric_line(a['metrics']),'']
        for cat,m in a['categories'].items():lines+=['- '+cat+f": {m['correct']}/{m['total']}"]
        lines+=['',f"参数有效 {a['argument_valid_count']}/{a['total_calls']}；真实 structured calls {a['native_structured_calls']}/{a['total_calls']}。",f"意图保留 {a['intent_review']['intent_preserving']}/{a['intent_review']['total']}（助手逐条工程判读，未独立人工复核）。",'']
    lines+=['## Latency', '', '单位 ms；p95 使用 numpy quantile 的线性插值，小样本不是稳定性能基准。LLM1/LLM2 指第一/第二次 HTTP 请求；有重试或多次调用的题保留全部请求，不把额外请求隐藏。']
    for split in ['dev','test']:
        for label,a in evidence[split].items():
            for group,values in a['latency'].items():
                for stage,d in values.items():
                    if d:lines+=[f"- {split}/{label}/{group}/{stage}: n={d['n']}, mean={d['mean']:.2f}, median={d['median']:.2f}, p95={d['p95']:.2f}"]
                    else:lines+=[f'- {split}/{label}/{group}/{stage}: unavailable']
    lines+=['', '本地 Qwen inference 主导 Agent E2E；不能与 Phase2 单独 retrieval latency 混为一谈。',
            'A0 dev 的 LLM2 分段耗时未持久化到逐题 trace（仅旧内存 summary 有值）；本文排除这些不可逐题复核值。LLM1/E2E/工具耗时有记录，原 trace 和 summary 未补写或重跑。此缺口已在 A1/A2 和正式 test 前修复，并有回归测试。',
            '', '## Trade-off 与限制', '']+['- '+x for x in evidence['limitations']]
    lines+=['', '## 完整性与证据', '',f"原始结果：`{evidence['raw_path_label']}`（ignored）；逐题 JSON、HTTP messages/tools、tool_calls、工具结果、角色传输、错误及摘要均保留。", f"原始 manifest hash：`{evidence['raw_manifest_sha256']}`。", '测试与冻结检查见证据快照的 validation 字段。', '工程原因分类仅为基于可观察行为的假设，不代表证明模型内部原因。']
    return '\n'.join(lines)+'\n'

def generate(run_dir,review_file,out,config_path=CONFIG_PATH):
    verify_run(run_dir)
    cfg=json.loads(config_path.read_text(encoding='utf-8'))
    lock=json.loads((run_dir/'routing_lock.json').read_text(encoding='utf-8'))
    body=dict(cfg);expected=body.pop('config_hash')
    if canonical_hash(body)!=expected or digest(config_path)!=lock['config_file_sha256'] or routing_sources()!=lock['source_hashes']:raise ValueError('configuration/source changed since freeze')
    review=json.loads(Path(review_file).read_text(encoding='utf-8'))
    evidence={'experiment':'v0.2-routing-first-official','checkpoint':'86c7325736de5c5a317ce8c59cb1178758dced80','dataset_checkpoint':'0b74d1968893c76b6c29f72af191c7529e74637e','selected_arm':cfg['selected_arm'],'config':cfg,'dev':{},'test':{},'manual_review':review,'limitations':review['limitations'],'validation':review['validation'],'raw_path_label':run_dir.relative_to(ROOT).as_posix()}
    bad_lines=['# V0.2 Routing Bad Cases','','所有 FN/FP 均保留；分类来自本轮助手逐条工程审阅，未独立人工复核，是原因候选而非因果证明。']
    for split,arms in [('dev',['A0','A1','A2']),('test',list(dict.fromkeys(['A0',cfg['selected_arm']])) )]:
        for arm in arms:
            cases=load_cases(run_dir,split,arm);label=split+'/'+arm
            if len(cases)!=(30 if split=='dev' else 20):raise ValueError('incomplete first attempt')
            s=summarize(cases);saved=json.loads((run_dir/split/arm/'summary.json').read_text(encoding='utf-8'))
            timing_note=audit_summary(s,saved,label)
            if timing_note:s['timing_audit']=timing_note
            s['intent_review']=review_calls(cases,review['calls'][label]);s['arm_config']=json.loads((run_dir/split/arm/'attempt.json').read_text(encoding='utf-8'))['arm']
            s['request_audit']=audit_requests(cases,s['arm_config'],cfg['tool_parameters_sha256'])
            evidence[split][arm]=s
            for c in cases:
                if c['confusion'] not in {'FN','FP'}:continue
                key=label+'/'+c['id'];analysis=review['bad_cases'][key]
                if not analysis.get('causes') or not set(analysis['causes'])<=CAUSES:raise ValueError('invalid engineering cause')
                bad_lines+=['','## '+key+' — '+c['confusion'],'', '- Category: '+c['category'],'- Input: '+c['query'],'- Expected route: '+str(c['expected_tool']),'- Actual calls: '+json.dumps(c['tool_calls'],ensure_ascii=False),'- First response: '+str(c['responses'][0]['content'] if c['responses'] else c.get('error')),'- Suspected causes: '+', '.join(analysis['causes']),'- Engineering analysis: '+analysis['reason']]
    bad_lines+=['','## 不混淆失败层','',review['interpretation_notes']]
    manifest={p.relative_to(run_dir).as_posix():digest(p) for p in sorted(run_dir.rglob('*.json')) if p.name!='raw_manifest.json'}
    write_once(run_dir/'raw_manifest.json',manifest)
    evidence['raw_manifest_sha256']=digest(run_dir/'raw_manifest.json');evidence['raw_manifest']=manifest
    write_once(out/'evidence/PHASE3_ROUTING.json',evidence)
    out.mkdir(parents=True,exist_ok=True)
    with (out/'ROUTING_REPORT.md').open('x',encoding='utf-8',newline='\n') as f:f.write(render_report(evidence))
    with (out/'ROUTING_BAD_CASES.md').open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(bad_lines)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['run-dir','review-file','output-dir']:p.add_argument('--'+name,required=True)
    p.add_argument("--config-file",default=str(CONFIG_PATH))
    a=p.parse_args();generate(Path(a.run_dir).resolve(),a.review_file,Path(a.output_dir).resolve(),Path(a.config_file).resolve())
if __name__=='__main__':main()
