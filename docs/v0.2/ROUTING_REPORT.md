# V0.2 Phase 3A — Routing A/B

这是独立 V0.2 实验。V0.1 结果、Phase2 检索实验和默认 Agent/Tool/Provider 保持不变。

## 协议与复现

单模型 Qwen3:1.7b、Ollama、本地 HTTP、真实 nanobot AgentRunner、单个只读 search_knowledge_base。每题全新上下文；用 Phase2 的冻结 Dense 索引，未启用 Hybrid。
A0 复用 V0.1 描述与指令；A1 只改通用描述；A2 改描述和通用私有资料指令；无 few-shot、实体白名单或人工指定调用。
先完成 dev30 ×3 arms，按预注册规则选择，再锁定配置。test20 的 A0 与选中方案各运行一次；若选 A0 则只运行一份。失败保留，未挑选重复结果。

```powershell
python scripts/v0_2/run_routing.py --stage init --run-dir artifacts/v0.2/routing/<new-run>
python scripts/v0_2/run_routing.py --stage dev --run-dir artifacts/v0.2/routing/<new-run>
# 将证据快照中的 A1/A2 config 保存为 JSON，再分别加 --arm-file 执行 dev。
python scripts/v0_2/run_routing.py --stage lock --run-dir artifacts/v0.2/routing/<new-run> --config-file artifacts/v0.2/routing/<new-run>/routing_config.json
python scripts/v0_2/run_routing.py --stage test --run-dir artifacts/v0.2/routing/<new-run> --config-file artifacts/v0.2/routing/<new-run>/routing_config.json
python scripts/v0_2/report_routing.py --run-dir artifacts/v0.2/routing/<new-run> --config-file artifacts/v0.2/routing/<new-run>/routing_config.json --review-file <manual-review.json> --output-dir artifacts/v0.2/routing/<new-run>/report
```
使用已安装当前项目插件的 nanobot venv。必须先具备冻结的 Phase2 Dense 索引。正式配置只写一次；独立复现实验使用 --config-file 保存新配置到新 artifacts 目录，不能覆盖本次正式配置与证据。

## Dev 选择

- A0: TP=16, FP=0, FN=5, TN=9; Accuracy=83.3333%, Precision=100.0000%, Recall=76.1905%, F1=86.4865%
- A1: TP=14, FP=0, FN=7, TN=9; Accuracy=76.6667%, Precision=100.0000%, Recall=66.6667%, F1=80.0000%
- A2: TP=21, FP=1, FN=0, TN=8; Accuracy=96.6667%, Precision=95.4545%, Recall=100.0000%, F1=97.6744%

选中 **A2**。只依据 dev，先限制 FP 增量 ≤1、Precision 下降 ≤5 个百分点，再优先 Recall、更少 FP、较短文本。
配置内容 hash：`2a71a7f26d65f79f0eabdad8ed238835f7d601cd8d8773e2a13b2dd46494e655`。

## 首次正式 test

### A0

TP=10, FP=0, FN=5, TN=5; Accuracy=75.0000%, Precision=100.0000%, Recall=66.6667%, F1=80.0000%

- ambiguous_boundary: 3/4
- general_no_tool: 4/4
- private_multi_evidence: 1/4
- private_no_answer: 4/4
- private_single_fact: 3/4

参数有效 10/10；真实 structured calls 10/10。
意图保留 9/10（助手逐条工程判读，未独立人工复核）。

### A2

TP=15, FP=0, FN=0, TN=5; Accuracy=100.0000%, Precision=100.0000%, Recall=100.0000%, F1=100.0000%

- ambiguous_boundary: 4/4
- general_no_tool: 4/4
- private_multi_evidence: 4/4
- private_no_answer: 4/4
- private_single_fact: 4/4

参数有效 15/15；真实 structured calls 15/15。
意图保留 15/15（助手逐条工程判读，未独立人工复核）。

## Latency

单位 ms；p95 使用 numpy quantile 的线性插值，小样本不是稳定性能基准。LLM1/LLM2 指第一/第二次 HTTP 请求；有重试或多次调用的题保留全部请求，不把额外请求隐藏。
- dev/A0/no_tool/e2e_ms: n=14, mean=24612.90, median=25459.36, p95=37350.56
- dev/A0/tool/e2e_ms: n=16, mean=64226.60, median=61423.54, p95=87513.16
- dev/A0/tool/llm1_ms: n=16, mean=21606.30, median=19963.64, p95=31388.92
- dev/A0/tool/retrieval_tool_ms: n=16, mean=174.55, median=130.60, p95=351.77
- dev/A0/tool/llm2_ms: unavailable
- dev/A1/no_tool/e2e_ms: n=16, mean=26521.67, median=22243.39, p95=40921.65
- dev/A1/tool/e2e_ms: n=14, mean=61132.90, median=55365.70, p95=90698.00
- dev/A1/tool/llm1_ms: n=14, mean=21083.65, median=19891.45, p95=25612.78
- dev/A1/tool/retrieval_tool_ms: n=14, mean=134.12, median=134.19, p95=155.13
- dev/A1/tool/llm2_ms: n=14, mean=39898.14, median=33490.87, p95=70864.43
- dev/A2/no_tool/e2e_ms: n=8, mean=39680.22, median=42891.47, p95=62243.02
- dev/A2/tool/e2e_ms: n=22, mean=75379.29, median=72080.14, p95=105866.90
- dev/A2/tool/llm1_ms: n=22, mean=28620.26, median=25731.74, p95=50154.11
- dev/A2/tool/retrieval_tool_ms: n=22, mean=176.02, median=166.77, p95=250.58
- dev/A2/tool/llm2_ms: n=22, mean=46561.96, median=44860.14, p95=77829.93
- test/A0/no_tool/e2e_ms: n=10, mean=48923.75, median=44761.35, p95=73863.65
- test/A0/tool/e2e_ms: n=10, mean=89871.68, median=81140.57, p95=127140.27
- test/A0/tool/llm1_ms: n=10, mean=33056.34, median=29092.16, p95=48599.21
- test/A0/tool/retrieval_tool_ms: n=10, mean=634.77, median=238.77, p95=1439.98
- test/A0/tool/llm2_ms: n=10, mean=56157.54, median=50113.05, p95=90151.28
- test/A2/no_tool/e2e_ms: n=5, mean=39486.85, median=41473.18, p95=51172.78
- test/A2/tool/e2e_ms: n=15, mean=82741.98, median=79239.01, p95=122448.40
- test/A2/tool/llm1_ms: n=15, mean=33796.57, median=32081.07, p95=49994.65
- test/A2/tool/retrieval_tool_ms: n=15, mean=222.79, median=208.82, p95=299.73
- test/A2/tool/llm2_ms: n=15, mean=48698.48, median=46304.34, p95=79045.96

本地 Qwen inference 主导 Agent E2E；不能与 Phase2 单独 retrieval latency 混为一谈。
A0 dev 的 LLM2 分段耗时未持久化到逐题 trace（仅旧内存 summary 有值）；本文排除这些不可逐题复核值。LLM1/E2E/工具耗时有记录，原 trace 和 summary 未补写或重跑。此缺口已在 A1/A2 和正式 test 前修复，并有回归测试。

## Trade-off 与限制

- Controlled synthetic corpus：40短文档/40 chunks；test仅20题、每类4题；Qwen3:1.7b单模型、单只读知识库Tool，不能证明生产可靠性或推广到其他场景。
- A2仅按dev预注册规则选择；dev增加1个FP（v2-a-020）；正式test A0 15/20 vs A2 20/20，仅本次小样本观测，不宣称统计显著性。
- 正式test每方案一次、temperature=0.1，未额外设seed；无跨机器确定性保证，顺序运行和设备/cache负载可能影响耗时。
- 本次控制会话中断，原Python子进程继续完成A0/A2，退出码0。恢复读取时各20/20，无missing-ID resume，无已完成题重跑或覆盖；原started_at和latency保留。
- 工具参数合法和语义意图判读不等于证据完整或答案正确；工程判读由本轮coding assistant逐条完成，无独立人工复核，也无额外judge模型。
- A2 test路由20/20仍存在跨实体推测、审计/备份混淆、检索漏必要证据以及无答案工位幻觉；v2-a-049不能因Tool成功就计作正确答案。
- A0 dev逐题JSON缺LLM2耗时，仅原内存summary有值；报告排除不可逐题复核数据，原始文件不补写、不重跑。
- 未启用Hybrid、threshold、reranker、few-shot或新模型；A2为实验配置，未修改默认插件描述、WebUI或nanobot core。

## 完整性与证据

原始结果：`artifacts/v0.2/routing/phase3_first_20261005`（ignored）；逐题 JSON、HTTP messages/tools、tool_calls、工具结果、角色传输、错误及摘要均保留。
原始 manifest hash：`63dc99fbcdbda473e4a06b1f2f0b7857c98f68f24b66ff9c612a2083c1e66076`。
测试与冻结检查见证据快照的 validation 字段。
工程原因分类仅为基于可观察行为的假设，不代表证明模型内部原因。

## 中断与恢复审计

本次发生的是控制会话中断；原 Python 子进程继续运行并自然完成，退出码 0。恢复时只轮询保留的执行会话和只读检查进程，没有新启动正式 test。未能事后恢复原进程 PID/CPU，它们未持久化；不把缺少这些信息解释为 hang。
- Run ID：`phase3_first_20261005`；原正式 started_at：`2026-10-05T05:21:22.727667+00:00`（北京时间 2026-10-05T13:21:22+08:00）。
- A2 config 锁定：2026-10-05T13:20:41+08:00，早于正式 test；内容 SHA256：`2a71a7f26d65f79f0eabdad8ed238835f7d601cd8d8773e2a13b2dd46494e655`；文件 SHA256：`4c3df3f3a34215383c76fbde507851a142d81741f8112799bd090ff9495f61d8`。
- 恢复读取时 A0=20/20、A2=20/20；missing-ID resume=false，resumed IDs=[]，没有重跑或覆盖已完成题；原 started_at、每题 latency 与原文件 hash 保留。
- 当前无存活 routing test Python 进程。所有首次正式 JSON 可解析、无重复 ID、无 partial/tmp 文件；A1 未运行正式 test。
- A0 original started_at：2026-10-05T05:21:25.689088+00:00；summary 完成落盘：2026-10-05T13:44:34+08:00。
- A0 completed IDs：`v2-a-001`, `v2-a-002`, `v2-a-003`, `v2-a-004`, `v2-a-005`, `v2-a-006`, `v2-a-007`, `v2-a-008`, `v2-a-009`, `v2-a-010`, `v2-a-021`, `v2-a-022`, `v2-a-023`, `v2-a-024`, `v2-a-025`, `v2-a-046`, `v2-a-047`, `v2-a-048`, `v2-a-049`, `v2-a-050`。
- A0 missing IDs：[]；duplicate IDs：[]。
- A2 original started_at：2026-10-05T05:44:36.875297+00:00；summary 完成落盘：2026-10-05T14:08:36+08:00。
- A2 completed IDs：`v2-a-001`, `v2-a-002`, `v2-a-003`, `v2-a-004`, `v2-a-005`, `v2-a-006`, `v2-a-007`, `v2-a-008`, `v2-a-009`, `v2-a-010`, `v2-a-021`, `v2-a-022`, `v2-a-023`, `v2-a-024`, `v2-a-025`, `v2-a-046`, `v2-a-047`, `v2-a-048`, `v2-a-049`, `v2-a-050`。
- A2 missing IDs：[]；duplicate IDs：[]。

## A0 → A2 配对结果与 trade-off

A0 15/20 → A2 20/20；TP 10→15、FP 0→0、FN 5→0、TN 5→5。Accuracy +25 个百分点，Precision 不变，Recall +33.33 个百分点，F1 +20 个百分点。变化来自更少 FN，没有新增 test FP。
- A0 错/A2 对（仅路由）：v2-a-003, v2-a-005, v2-a-007, v2-a-008, v2-a-023。
- A0 对/A2 错（仅路由）：无；A0/A2 都错（仅路由）：无。这两类本次没有实际样本，不构造虚拟案例。
- general_no_tool：4/4→4/4；private_single_fact：3/4→4/4；private_multi_evidence：1/4→4/4；private_no_answer：4/4→4/4；ambiguous_boundary：3/4→4/4。
- Dev 中 A2 仍有 FP v2-a-020，不能用 test 的零 FP 宣称该风险消失。A1 dev 23/30，低于 A0 25/30；改长 Tool Description 本身并未保证更好路由。
- A2 选择时 dev 的 Recall=21/21，FP 比 A0 多 1，Precision 从100%降到95.45%，在预注册≤5个百分点损失/≤1新增FP界限内；未使用test结果重新选择。

## 工具协议与 query rewrite 复核

- 正式 A0：有效参数10/10；保守意图保留9/10（v2-a-049丢失升级协调角色限定）。A2：有效参数15/15；意图保留15/15。跨dev/test所有实际调用均有逐条理由，见证据 JSON 的 manual_review.calls。
- A2 15/15 是 Qwen 真实 structured calls；tool name、query、整数 top_k=1..10、无额外字段和schema hash均通过。不是用字符串相等判query是否正确。
- 正式两arm合计65次模型HTTP请求均200；25个tool_call_id与assistant调用匹配，25个工具结果正文与后续role=tool内容逐字一致。每题仍全新上下文；初始system/user不含gold标签或答案。
- v2-a-048 两个改写都保留“一线/二线、角色、响应时间”；A0 Top3含二线证据，A2 Top3没有必要证据。这是现有首次结果的coverage退化，不能据此声称query语义必定丢失，也未重跑原query挑结果。

## 保留的答案质量问题

以下是首次trace的工程观察，不是另一次完整答案benchmark，也没有更改路由指标。20/20 route correctness 绝不等于20/20 answer correctness。
- A2/v2-a-002 — generation/evidence interpretation：主答案 RX-41 正确，但追加“验收要求不记录在该卡中”与该卡明确96小时矛盾；原卡说不记录Aurora（非Aurora-X）的验收要求。
- A2/v2-a-005 — generation/entity evidence interpretation：186000预算正确，但将 Aurora-X / FIN-AX12 的32000采购上限推给 FIN-A12；query意图完整、证据存在，属于跨实体推测。
- A2/v2-a-023 — retrieval coverage + generation：Top3只有SABLE-18B模型、SABLE-18B备份、SABLE-18备份，漏sable18_audit；在线审计应60天，回答误为14天。
- A2/v2-a-048 — retrieval coverage + generation：Top3无一线/二线必要chunk；模型未给出期望D-11/15分钟与D-22/45分钟，并把无关机器人维护角色作为补充。A0同题Top3含二线卡，A2零必要证据；意图保留不保证证据保留。
- A0 and A2/v2-a-049 — generation/no-answer hallucination：两者均错误把角色D-33说成工位编号；工具返回无工位事实。A0还把一线15分钟附给升级协调角色。
- A2/v2-a-050 — generation/condition interpretation：20分钟数值正确，但部分句子变成“一线响应未满20分钟”，未清楚表达未响应持续满20分钟，存在触发条件措辞错误。
- A0/v2-a-001 — general answer generation：无工具路由正确，但声称对变量重新赋字符串会报错，这是普通Python知识回答错误。

## 回归与冻结验证

- 全部pytest 164通过：原37 + dataset40 + retrieval52 + routing35；插件验证11通过；独立指标检查3通过。合计178项独立验证，Agent正式40个case不计入这个测试数。
- V0.1 25 hashes、V0.2 45 hashes、Phase2全部原始/evidence文件、原index/metadata、历史Phase2/3A/3B evidence均保持一致。nanobot Git clean，默认Provider/Tool/Retriever与README没有改动。
- V0.1 tag仍为 aa422d826fa484933d9949c16fc79e1a2f22eda1；当前仍在 feat/v0.2-eval-hybrid，未commit/push。
- 运行代码/配置在正式test锁定后的source/file hashes一致；报告仅聚合首轮原始结果。raw manifest封存原JSON，recovery_provenance保留正式test的逐文件hash。

## Phase 3.5 — Result Audit / Freeze Checkpoint

本节记录提交前审计；前文“未commit/push”是 Phase 3A 生成报告时的历史状态。正式 trace、latency、配置和证据快照均未覆盖。

- 冻结順序：A2 根据30条dev预注册规则选出；2026-10-05 13:20:41 +08:00 锁定，正式test于13:21:22 +08:00开始。全部dev题完成早于锁定。
- 文件SHA256：`4c3df3f3a34215383c76fbde507851a142d81741f8112799bd090ff9495f61d8`；配置内容SHA256：`2a71a7f26d65f79f0eabdad8ed238835f7d601cd8d8773e2a13b2dd46494e655`。正式test后源码hash、Prompt与Tool Description未变化。
- 原始manifest与恢复记录逐文件hash通过，A0/A2均为首次结果；会话中断期间原子进程继续完成，没有重跑或覆盖。
- 独立复算直接读取frozen标签和真实tool_calls，不调用本实验routing_metrics：A0 TP10/FP0/FN5/TN5，Accuracy75%、Precision100%、Recall66.67%、F1 80%；A2 TP15/FP0/FN0/TN5，四项均100%。与summary及证据快照一致。
- 工程抽查：v2-a-003（两职责）及007（上线角色）均A0 FN→A2 TP；001 general_no_tool两者TN；004 private_no_answer两者TP；005 ambiguous_boundary为A0 FN→A2 TP。标签、实际调用和confusion一致，不把最终答案失败计作routing FN。
- 保留A1负结果：23/30（76.67%）低于A0 25/30（83.33%）。本轮仅改Tool Description没有改善路由；加上explicit routing instruction的A2为29/30 dev、20/20 test。这是当前组合配置的观测，不证明普遍因果。
- 100%边界：test only 20 queries，5 categories × 4，synthetic controlled benchmark，单Qwen3:1.7b和单knowledge-base Tool。A2 dev仍有1个FP；routing correctness ≠ final answer correctness，不代表production reliability。
- 路由成功但retrieval/grounding/answer失败仍保留：预算跨项目推测、审计与备份保留时间混淆、multi-evidence遗漏、D-33角色/工位混淆；作为后续Phase 3B/4输入，本次不修算法或Prompt。
- 本轮重新执行164 pytest（38.29秒）、11 plugin verification、3 independent metric checks，178项全部通过。V0.1 25 hashes、V0.2 45 hashes、Phase2证据、旧索引、A2配置保持一致，nanobot clean，旧tag不变。
- 精简证据继续保存在`docs/v0.2/evidence/PHASE3_ROUTING.json`，未修改；新的只读审计记录在ignored `artifacts/v0.2/routing/phase3_5_audit_20261005/audit.json`，不提交原始trace/cache。
