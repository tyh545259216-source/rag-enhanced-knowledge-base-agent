# V0.2 Phase 4A — No-answer / Similarity Threshold Feasibility

## Protocol

复用Phase2首次Dense dev/test JSON，不调用Embedding、FAISS search或LLM。正类no-answer；score<threshold判insufficient evidence，等于阈值判answerable。仅dev 36题（30/6）扫描；候选锁定后一次应用test 24题（20/4）。
score越高仅表示embedding similarity，不是answer probability，也不能证明是否存在完整答案。margin仅描述，不参与预测。

## Dev distributions

- answerable: {"count": 30, "min": 0.6408094167709351, "max": 0.8980100154876709, "mean": 0.7954264720280965, "median": 0.8269739747047424, "p10": 0.6506380200386047, "p25": 0.7443390637636185, "p75": 0.8652000278234482, "p90": 0.8836321711540223}
- no_answer: {"count": 6, "min": 0.8182495832443237, "max": 0.8761948347091675, "mean": 0.8430303633213043, "median": 0.8448676466941833, "p10": 0.8215188384056091, "p25": 0.8293854594230652, "p75": 0.8485502153635025, "p90": 0.8627046048641205}
- top1-top2 answerable: {"count": 30, "min": 0.0008522272109985352, "max": 0.14435070753097534, "mean": 0.0420667827129364, "median": 0.031118243932724, "p10": 0.013521045446395874, "p25": 0.022187307476997375, "p75": 0.055349111557006836, "p90": 0.07757722139358522}
- top1-top2 no_answer: {"count": 6, "min": 0.0052550435066223145, "max": 0.042674899101257324, "mean": 0.026287684837977093, "median": 0.030695170164108276, "p10": 0.008997350931167603, "p25": 0.01616133749485016, "p75": 0.03549061715602875, "p90": 0.039170533418655396}

## Overlap

{"answerable_min": 0.6408094167709351, "no_answer_max": 0.8761948347091675, "interval": [0.8182495832443237, 0.8761948347091675], "no_answer_in_answerable_range": {"count": 6, "total": 6, "ids": ["v2-r-018", "v2-r-024", "v2-r-036", "v2-r-042", "v2-r-048", "v2-r-054"]}, "answerable_in_no_answer_range": {"count": 11, "total": 30, "ids": ["v2-r-016", "v2-r-021", "v2-r-031", "v2-r-033", "v2-r-034", "v2-r-039", "v2-r-040", "v2-r-043", "v2-r-045", "v2-r-046", "v2-r-051"]}}

## Candidate selection

预注册网格0.50至0.95、步长0.01共46个候选；用exact Fraction比较F1/FRR/precision，最终同指标选择最低阈值以减少拒绝风险。任何test分数都不参与scan/选择。
Selected threshold: 0.85; config hash: `f3d30c433a70b3e878f23e61dfd522a7566b830c2f0adac9e2bde64d7c34473e`.
Dev metrics: {"threshold": 0.85, "positive_class": "no_answer", "TP": 5, "FP": 19, "FN": 1, "TN": 11, "no_answer_precision": 0.20833333333333334, "no_answer_recall": 0.8333333333333334, "no_answer_f1": 0.3333333333333333, "answerable_false_rejection_rate": 0.6333333333333333, "accuracy": 0.4444444444444444, "answerable_count": 30, "no_answer_count": 6, "false_rejection_ids": ["v2-r-013", "v2-r-014", "v2-r-016", "v2-r-017", "v2-r-019", "v2-r-020", "v2-r-031", "v2-r-032", "v2-r-037", "v2-r-038", "v2-r-040", "v2-r-044", "v2-r-045", "v2-r-047", "v2-r-049", "v2-r-050", "v2-r-051", "v2-r-052", "v2-r-053"], "missed_no_answer_ids": ["v2-r-036"]}

## Frozen test

{"threshold": 0.85, "positive_class": "no_answer", "TP": 1, "FP": 11, "FN": 3, "TN": 9, "no_answer_precision": 0.08333333333333333, "no_answer_recall": 0.25, "no_answer_f1": 0.125, "answerable_false_rejection_rate": 0.55, "accuracy": 0.4166666666666667, "answerable_count": 20, "no_answer_count": 4, "false_rejection_ids": ["v2-r-001", "v2-r-002", "v2-r-003", "v2-r-004", "v2-r-007", "v2-r-008", "v2-r-010", "v2-r-011", "v2-r-025", "v2-r-055", "v2-r-056"], "missed_no_answer_ids": ["v2-r-006", "v2-r-030", "v2-r-060"]}
No-answer detected 1/4; answerable wrongly rejected 11/20.

## Decision

C: Dev上6/6 no-answer落入answerable范围、11/30 answerable落入no-answer范围；仅dev选定0.85后，test检出1/4无答案却误拒11/20有答案。score overlap严重，fixed threshold在当前benchmark不可靠，不值得接入默认pipeline。
在当前benchmark：fixed similarity threshold may not reliably separate answerable and no-answer queries。这里的局限由有限样本的重叠/误拒证据支持，不是普遍理论定理。
未将threshold接入Retriever、Tool、Router或默认pipeline。没有test后调参或特殊query规则。

## Historical comparison

复用首次test中最高no-answer Top1=0.896122（历史约0.8961）。它表示相似内部主题，不证明所问属性有答案。V0.1无答案查询仍返回Top-K的观察与此一致；不混合两语料的分数作校准。

## Limitations

- synthetic corpus; 40-chunk controlled benchmark
- dev no-answer only 6; test no-answer only 4
- single nomic-embed-text embedding model, normalized FAISS IndexFlatIP, Dense Top1 score only
- manually designed corpus/questions; no statistical significance claim
- threshold may not generalize to other corpora/models
- 历史test最高no-answer分数已公开，不宣称此前完全blind；本轮只用dev确定规则与候选，没有用test调参
- predicted no-answer is a score-based proxy for insufficient evidence, not proof of corpus answer absence
- Top5以外的relevant rank为unknown，不代表不存在或获得全库排名

## Reproduction

```powershell
python scripts/v0_2/analyze_no_answer.py --stage dev --run-dir artifacts/v0.2/no_answer/<new-run>
python scripts/v0_2/analyze_no_answer.py --stage test --run-dir artifacts/v0.2/no_answer/<new-run>
python scripts/v0_2/analyze_no_answer.py --stage report --run-dir artifacts/v0.2/no_answer/<new-run> --decision C --reason 'engineering interpretation; no threshold tuning'
```
依赖本地保存的Phase2 raw Dense结果；缺文件/字段停止，不重跑official test。新run目录的REPORT.md和export/PHASE4_THRESHOLD.json为新本地派生输出。--publish仅首次创建两个正式docs，拒绝覆盖历史。threshold config/source hash不符就停止。
原始manifest覆盖本轮分析输入/输出JSON与REPORT.md；排除manifest本身及其派生export，避免自引用hash。

## Readable result summary

| Dev Top1 statistic | Answerable (30) | No-answer (6) |
|---|---:|---:|
| count | 30 | 6 |
| min | 0.640809 | 0.818250 |
| max | 0.898010 | 0.876195 |
| mean | 0.795426 | 0.843030 |
| median | 0.826974 | 0.844868 |
| p10 | 0.650638 | 0.821519 |
| p25 | 0.744339 | 0.829385 |
| p75 | 0.865200 | 0.848550 |
| p90 | 0.883632 | 0.862705 |

Top1分布交集按min/max envelope定义为[0.818250, 0.876195]，不是密度重叠面积。No-answer 6/6落在answerable范围内，answerable 11/30落在no-answer范围内。No-answer均值0.843030甚至高于answerable均值0.795426；本语料里高分往往来自相似实体/编号，不是所问属性的存在证明。
辅助margin：answerable mean/median=0.042067/0.031118，no-answer=0.026288/0.030695；范围分别[0.000852,0.144351]与[0.005255,0.042675]，仍重叠。未扫描margin阈值，也未组合成classifier。

| Split, fixed threshold 0.85 | TP / FP / FN / TN | No-answer precision | Recall | F1 | Answerable false rejection | Overall accuracy |
|---|---|---:|---:|---:|---|---:|
| dev | 5 / 19 / 1 / 11 | 20.83% | 83.33% | 33.33% | 19/30 (63.33%) | 16/36 (44.44%) |
| frozen test | 1 / 11 / 3 / 9 | 8.33% | 25.00% | 12.50% | 11/20 (55.00%) | 10/24 (41.67%) |

正类明确为no-answer：TP=无答案且被拒；FP=有答案却被拒；FN=无答案但通过；TN=有答案且通过。score=threshold时通过，不四舍五入分数再比较。Undefined precision等按预注册规则记0，并同时保留计数。
只在dev扫描46个候选，F1/FRR/precision通过exact fractions排序，最后取同指标中最低阈值。最佳dev F1也只有1/3；没有因为Accuracy的类别不平衡而选一个全判answerable的规则。Test不扫描第二套阈值，单次候选结果即正式负结果。

## Concrete failure observations

- Dev v2-r-050：正式运行审计管理/保留问题是answerable，Top1只有0.640809，所需ret_prod块在rank 3；用0.85会拒绝有答案问题。
- Dev v2-r-036：ORBIT-3容纳人数未记载，Top1却0.876195，超过固定0.85而未被检出。
- Test v2-r-006：RX-41电池容量未记载，Top1=0.896122（margin=0.097418），高分和较大gap都不能在该实例证明答案存在。
- Test检出的唯一no-answer是v2-r-012（Borealis-2销售价，Top1=0.789981）；未检出006/030/060。11个误拒ID与全部Top1/Top2/Top3及saved Top5中的relevant ranks保存在原始JSON和证据中，不删除失败题。
冻结answerable标签表示corpus存在required evidence；不保证本次Top-K证据完整。本实验不评测最终LLM回答或幻觉率，insufficient evidence只是score规则的代理预测。

## Validation and frozen integrity

本阶段新增29项纯离线算法/阶段协议测试。全部真实口径为220 pytest + 11 plugin verification + 3 independent metric checks = 234，全通过；pytest耗时13.47秒。前一次审批超时的三项命令均未执行；按返回允许重试一次后完成，不重复统计。
保护校验：V0.1 25 hash、V0.2 45 hash、196个既有受保护文件、Phase2/Phase3 routing/Phase3 ablation evidence及raw、A2 config、旧index/metadata均不变；nanobot clean。HEAD仍214b5e5a35645768485ca2232a0b85b0b586389b，V0.1 tag仍aa422d826fa484933d9949c16fc79e1a2f22eda1。没有commit/push/README/简历/默认Tool修改。
候选config锁定UTC 2026-10-05 15:11:36.784643，test一次应用开始UTC 15:12:27.786172；当地时间Asia/Shanghai分别为23:11:36与23:12:27。config/rule/source hashes在test后未改变。
新增可审阅文件为no_answer分析包、THRESHOLD_CONFIG、CLI、tests以及两个文档。所有原始分数、46条scan、单次test预测和validation留在ignored artifacts/v0.2/no_answer/phase4a_first_20261005/；raw_manifest保持封存，当前公开报告只补充解释，不修改原始结果。

结论C是正式负结果：在当前40-chunk controlled synthetic corpus、nomic-embed-text和Dense Top1定义下，fixed similarity threshold may not reliably separate answerable and no-answer queries。本轮不接入默认pipeline，不再为使结果变好而调threshold。dev/test无答案只有6/4题，不能外推到其他语料、模型或生产环境。

## Phase 4.5 audit and freeze checkpoint

审计日期：2026-10-06（Asia/Shanghai）。独立审计直接读取 Phase2 首次 frozen Dense dev/test results，用标准库重新计算分布、margin、overlap、dev 候选排序与固定 0.85 的混淆矩阵；没有调用本实验的 extraction/metrics/selection 实现，没有重跑 retrieval/model，没有创建第二次正式 test 结果。所有指标、46 条 dev scan 及 config/hash 与 Phase4A 一致。

人工抽查五个案例：

- v2-r-012（test，TP）：Borealis-2 销售价未记载，Top1=0.789981；固定规则正确检出 no-answer。
- v2-r-036（dev，FN）：ORBIT-3 容量未记载，Top1=0.876195 命中 ORBIT-3A 的 26 人；固定规则漏检，不能将相似实体的容量移用。
- v2-r-013（dev，FP）：ARC-TF 的期限 21 天已在 Top1，score=0.806210；有明确证据却被误拒。
- v2-r-050（dev，FP）：生产审计角色 L-11、保留 120 天在 rank 3；Top1=0.640809，规则误拒 corpus 中有答案的问题。
- v2-r-006（test，FN）：RX-41 电池容量未记载，Top1=0.896122 只匹配设备与验收信息；高 similarity 不证明目标属性有答案。

冻结顺序由原始 lock、test_attempt、selected_config、config/source hashes 与 sealed raw manifest 核验：候选 config 先冻结，再单次正式应用 test；没有 test 后修改 threshold/selection rule。历史 test 高分已公开的限制继续保留，不宣称此前完全 blind。当前审计的独立复算不是新的候选选择或第二次正式 test。

正式结论仍为 C，仅限当前 corpus、nomic-embed-text、Dense Top1 benchmark。默认 pipeline 不接入 fixed threshold；不提出第二套阈值或 query 特判。原始 Phase4A raw manifest/outputs 保持不变，审计证据另存 ignored artifacts/v0.2/no_answer/phase4_5_audit_20261006/。

### V0.2 scope closure: no Phase 4B feature extension

V0.2 的目标是实验验证，本版本不继续实现 LLM Evidence Judge、Reranker、Multi-stage abstention、MCP、LangGraph、Memory 或 GraphRAG。保留负结果，不通过堆功能改变本轮结论。这些能力没有接入当前系统。

Phase4.5 重新运行全部验证：220 pytest（20.44 秒）、11 plugin verification、3 independent metric checks，共 234 项全部通过。未改变现有测试口径；既有 V0.1 25 hashes、V0.2 dataset 45 hashes、Phase2/3 evidence、A2、旧 index/metadata、nanobot clean 与 V0.1 tag 再次核验通过。本 checkpoint 仅提交 Phase4 的 8 个代码/配置/测试/报告文件，不提交 ignored raw/cache，不修改 main、README 或简历。
