# V0.2 Experimental Evaluation Summary

Release type: **experimental evaluation release**。V0.2 是 V0.1 功能 baseline 上的实验增强版，不是架构重写或 production release。首次正式结果、配置、失败样本和人工判断均保留；本总结不重跑、不重算替换历史结果。

## 1. 为什么开始 V0.2

V0.1 已验证 Retriever、外部工具、structured tool calling 与自主路由，但 9 个资料块不足以回答“换一种检索/路由策略是否真的更好”。V0.2 因此先构建可审计的冻结数据，再对检索覆盖、工具决策、最终答案和拒答分别做实验，不以新增技术栈为目标。

默认可运行系统仍为 nanobot → Qwen3 → 可选只读 Tool → Dense Retriever → role=tool → Qwen3。实验实现与默认路径分离。

## 2. Dataset freeze：先固定问题，再观察模型

- 40 个不同虚构 TXT 文档、40 个实际 chunks，10 个主题组；不是把 V0.1 的 9 条机械切碎。
- Retrieval 60：dev 36 / test 24；6 类各 dev 6 / test 4。Test 为 20 answerable + 4 no-answer；后者不计 HitRate/Recall/MRR。
- Routing 50：dev 30 / test 20；5 类各 dev 6 / test 4，包括无需工具、私有单事实、多证据、私有无答案与边界任务。
- family_id 按主题分组，60% dev / 40% test。40 documents → 40 chunks 是 controlled synthetic retrieval benchmark，不证明长文档 chunking 性能。
- corpus/dev/test 的 45-file manifest 在模型实验前冻结。Dev 可用于预注册选择；test 禁止调 Prompt、标签、答案或删失败题。相似实体、职责、编号、数字/日期、多证据与未记载属性均有标注。

[Dataset report](DATASET_REPORT.md) · [Freeze](DATASET_FREEZE.md) · [manifest](../../eval/v0.2/freeze_manifest.json)

## 3. Retrieval comparison：coverage 与排名不是同一收益

正式首次 test（24 题，6 类各 4 题，指标分母 20 answerable）：

- Dense：HitRate@3 **90%**；Recall@3 **83.33%**；MRR@3 **0.7333**。
- BM25：HitRate@3 **95%**；Recall@3 **90%**；MRR@3 **0.8917**。
- Hybrid：HitRate@3 **100%**；Recall@3 **97.50%**；MRR@3 **0.8750**。

本次 Hybrid Top-K evidence coverage 最高；BM25 first-relevant ranking/MRR 更好。Hybrid improves Top-K evidence coverage in this benchmark, but does not dominate first-relevant ranking quality. 不使用“全面领先”“显著提升”或普遍最优的说法。

配置：nomic-embed-text、L2 normalization、FAISS IndexFlatIP（实际 768 维）；BM25 tokenizer `nfkc-ascii-id-cjk12-v1`，k1=1.5、b=0.75；RRF k=60、candidate pool=20；K=1/3/5。配置在首次 test 前锁定，未事后选择更好一轮。

Semantic paraphrase test 仅 4 题，仍有明显实体/关键词；BM25 4/4、Dense 2/4 Hit@3 不能推出 BM25 普遍更擅长语义改写。相似实体匹配也不能证明目标事实有答案。

[Report](RETRIEVAL_REPORT.md) · [Evidence](evidence/PHASE2_RETRIEVAL.json)

## 4. Routing A/B：只改描述不保证有效

Dev 30 题：A0 **25/30（83.33%）**，A1 **23/30（76.67%）**，A2 **29/30（96.67%）**。A1 只扩展 Tool Description，负结果没有删除；A2 结合 Tool Description 与 explicit routing instruction，在预注册规则下由 dev 选定并冻结。

首次 frozen test 20 条、5 类各 4 条：

- A0：**15/20**，TP10/FP0/FN5/TN5；Accuracy 75%、Precision 100%、Recall 66.67%、F1 80%。
- A2：**20/20**，TP15/FP0/FN0/TN5；Accuracy/Precision/Recall/F1 均 100%。改善来自少了 5 个 FN，没有增加 FP。

A2 dev 仍有一个错误；20/20 仅是当前 single Qwen3:1.7b、single Tool、synthetic controlled test 的 routing 指标，不是 final answer、production reliability 或普遍因果结论。Test 后未改 instruction/schema/config。正式测试期间控制会话中断，原子进程继续完成；恢复 provenance 保留，没有重跑已完成题、覆盖或重新选 A2。

A2 配置仅属于受控实验，未写入默认 WebUI/Tool。路由成功后的预算推测、备份/审计混淆、多证据遗漏、角色/工位混淆仍保留。

[Report](ROUTING_REPORT.md) · [Bad cases](ROUTING_BAD_CASES.md) · [Evidence](evidence/PHASE3_ROUTING.json)

## 5. Agentic RAG Ablation：正确决定查库不等于正确答案

同一 20-query synthetic test，冻结 rubric 中 strict=(correct+correct_abstention)/20，partial 不计分：

- B0 Direct：Strict **7/20**；Tool Call Rate **0%**；unnecessary **0/5**；missed **15/15**。
- B1 Always Retrieve：Strict **15/20**；Tool Call Rate **100%**；unnecessary **5/5**；missed **0/15**。
- B2 Agent Routing：Strict **14/20**；Tool Call Rate **75%**；unnecessary **0/5**；missed **0/15**。

5 个无需检索样本包含 4 个 general_no_tool 和 1 个 boundary 文字处理；不能误写成 5 个 general 分类。B0 的 missed 是固定禁用检索策略，不是 Router 犯错。

Direct 对 private queries 明显不足；Always Retrieve 在本次实验中 strict final accuracy 最高。Agent Routing 避免了 5/5 不必要检索、没有 missed retrieval，但未全面优于 Always Retrieve 的最终答案质量。B2 routing 为 20/20，final answer 却只有 14/20。

B2 六个答案错误来自后续层：query rewrite（048）、检索排名/证据不完整（023/048）、事实类型/实体混淆（包括跨项目预算及 D-33 角色/工位）、generation/grounding。标签可重叠，不能相加当独立错误数量；没有将它们重新归为 routing failure。

### Latency 解释

E2E mean：B0 **31.13s**、B1 **50.06s**、B2 **71.93s**。Agent Routing 减少了 retrieval，但当前 runtime/local model 下未降低 E2E latency。B1 固定策略调度，没有 planning LLM；B2 通常 LLM1 + Tool + LLM2，规划耗时约 33.80s，远大于 retrieval 约 0.2s。

本地推理占主导，B0/B1 顺序执行、B2 复用较早首次 A2 trace，运行时段、调用数、输出长度与缓存未严格控制。这不是等成本性能实验，不能推出 Agent Routing 普遍更慢或 Always Retrieve 普遍更快。B2 没有重跑。人工判断及上下文复核均有 provenance，不声称完全 blind。

[Report](ABLATION_REPORT.md) · [Evidence](evidence/PHASE3_ABLATION.json)

## 6. No-answer threshold：保留正式负结果

只复用 Phase2 首次 Dense 分数，不重跑 retrieval/model。正类 no-answer，score<阈值预测无答案；相等时预测 answerable。Dev 36（30/6）在预定规则下选出 **0.85**，先冻结，再对 test 24（20/4）正式应用一次。

- Dev：TP5/FP19/FN1/TN11；Precision 20.83%、Recall 83.33%、F1 33.33%、Accuracy 44.44%；误拒 19/30，检出 5/6。
- Test：TP1/FP11/FN3/TN9；Precision **8.33%**、Recall **25%**、F1 **12.50%**、Accuracy **41.67%**；误拒 **11/20**，检出 **1/4**。

Dev min/max 范围交集 [0.818250,0.876195]；6/6 no-answer 落在 answerable 范围，11/30 answerable 落入 no-answer 范围。Test 最高 no-answer Top1 **0.896122**，匹配设备实体却缺少所问电池容量。High similarity does not imply answer existence in this benchmark。

正式 decision **C**：fixed Dense similarity threshold **NOT adopted**。限于当前 40-chunk corpus、nomic-embed-text、当前 benchmark；不声称 similarity threshold universally useless。历史高 test 分数已公开，不宣称此前完全 blind，但候选选择只用 dev，没有 test 后换阈值。Margin 仅描述，没有训练第二套 classifier。

[Report](NO_ANSWER_REPORT.md) · [Evidence](evidence/PHASE4_THRESHOLD.json)

## 7. Negative results 是交付的一部分

保留 A1 dev 退化、Hybrid MRR trade-off、Always Retrieve 比 Agent Routing 更高的 strict 分数、规划成本未换来更低 E2E、固定阈值的误拒与漏检。失败题和原始首次输出不删改，不能为简历隐藏这些结果。

## 8. Final decisions

默认 Dense Retriever、Embedding、FAISS、索引/metadata、只读 Tool、Provider、nanobot core 均保持原行为。A2、BM25/Hybrid 保留为冻结实验；其改善不是默认线上/WebUI 配置的性能承诺。V0.1 tag 不动，V0.2 dataset/evidence/config 不变。发布 manifest 记录阶段 checkpoint、配置与证据 hash、运行时、指标和回归口径。

V0.2 到此封版，不把 Hybrid 或 threshold 接入默认 Tool，不调模型/Prompt，不继续扩功能。

## 9. Limitations / reproduction boundaries

人工合成数据、短文单块、单工具/单模型、小样本、单次 Agent 采样；按主题分割仍共享任务模板，没有跨语料/模型泛化证据，不作统计显著性声明。Semantic paraphrase 每类 test 仅 4 条，no-answer test 仅 4 条。严格 final correctness、grounding 与 routing 是不同指标。

安装、默认 ingest/WebUI、测试与 smoke 见 [README](../../README.md)。完整实验入口：

- `scripts/v0_2/validate_datasets.py`：新 ignored 目录的 dataset JSON/Markdown；不使用 `--report` 覆盖冻结报告。
- `scripts/v0_2/run_retrieval.py`：独立新 run-dir 的 dev → lock → test，产物 JSON 与 test/REPORT.md。不要复用首次路径，test 不用于调配置。
- `scripts/v0_2/run_routing.py` / `report_routing.py`：新 run-dir/config-file 及人工 intent review；配置和历史 raw provenance 不可替代。固定 A2 的首次结果只读，不按 test 再选。
- `scripts/v0_2/run_ablation.py`：需要本地 Phase2 index、Phase3 raw 与冻结 rubric/人工 judgments；正式报告为排他创建，不是可覆盖的公共 benchmark 服务。
- `scripts/v0_2/analyze_no_answer.py`：离线复用首次 Phase2 raw，需要本地 JSON；dev/test/report 阶段不重跑模型。

GitHub 提交包含 corpus、golden、实现、公开 evidence 与报告；完整 raw trace、timing samples、binary index、模型、credentials 继续 ignored。缺少历史 raw 时报告证据仍可审阅，但不能声称可重建所有 token 流，也不能重跑冒充首次结果。完整 benchmark 耗时较高，不是安装必做步骤；本轮只跑回归。

## 10. What was NOT adopted

不接入默认 pipeline：Hybrid、fixed similarity threshold、A2 专用 instruction/Tool Description。未新增 Evidence Judge、Reranker、multi-stage abstention、MCP、Memory、LangChain、LangGraph、GraphRAG、Multi-Agent、Redis、Docker 或新大模型。

项目复用 nanobot runtime 与两份 MIT RAG 基础，原创工作范围是适配、接口、插件与分层实验，不将上游框架作为原创。见 [THIRD_PARTY_NOTICES](../../THIRD_PARTY_NOTICES.md)。历史审计中的未commit状态是生成时快照，当前状态以 Git 为准。

## Release regression and integrity

最终回归：220 pytest（33.96s）、11 plugin verification、3 independent metric checks，共 234 validation/test checks 全部通过；不是 benchmark query 数，也没有重跑正式 test。V0.1 25-file 与 V0.2 45-file manifest、Phase2/3/4 正式 evidence/config、旧 index/metadata、nanobot clean 和旧 tag 保持不变。PLAN 的环境迁移记录仅做本机目录占位符脱敏，未修改历史事实或正式结果；原始路径文本保留在 ignored 本地审计。

版本与 provenance 见 [V0_2_EXPERIMENTAL](../releases/V0_2_EXPERIMENTAL.json)。本轮只准备 feature branch 上的实验发布 checkpoint，不 merge、不 push、不创建 tag。
