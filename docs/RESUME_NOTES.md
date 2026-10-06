# Resume Notes — V0.2 Experimental Evaluation

中文项目名：基于工具调用的本地检索增强知识库 Agent 及分层评估
英文项目名：RAG-Enhanced Knowledge Base Agent with Tool Calling
技术栈：Python、Ollama、Qwen3:1.7b、nomic-embed-text、FAISS IndexFlatIP、BM25/RRF（实验）、PyMuPDF、pytest、nanobot External Tools。

**证据范围：小规模 controlled synthetic benchmark，非生产级。** V0.1 功能链路与 V0.2 实验分开描述，不将实验配置说成默认 WebUI 能力。本文件是可选素材，不修改用户 Word 简历。

## A. 简历可写

建议选 3–4 条，不把所有百分比堆进简历。数字必须带测试规模或 synthetic 语境：

### 中文候选

- 基于带来源记录的 MIT RAG 组件统一 PDF/TXT、chunk metadata 与 Retriever 接口，并通过 nanobot external entry point 集成只读知识库工具，验证真实 structured tool calling 与 role=tool 回传，不修改框架 core。
- 构建 40-chunk 虚构语料、60 条检索与 50 条路由题，按主题划分 dev/test 并冻结 hash；对照 Dense、BM25 与 RRF Hybrid，在 24-query synthetic retrieval test 上 Hybrid Recall@3 达 97.5%，同时保留 MRR trade-off。
- 基于 dev 比较 Tool Description 与 routing instruction；选定配置在 20-query frozen synthetic routing test 上达到 20/20，保留 baseline 15/20 与描述单独修改的负结果，不外推到生产可靠性。
- 设计 Direct / Always Retrieve / Agent Routing 消融，分层评估证据、路由、grounding 与答案；Agent Routing 在 20-query synthetic test 中避免 5/5 不必要检索，但 strict final 为 14/20，未全面优于 Always Retrieve。

较短的第三条可写：开展受控路由与消融评估，验证自主路由能避免不必要的知识库执行，并定位检索、改写和证据理解导致的最终答案错误。

### English candidates

- Adapted attributed MIT RAG components into a unified Retriever and integrated a read-only knowledge tool through nanobot's external entry point, validating native structured calls and tool-result transport without modifying runtime core.
- Built a 40-chunk synthetic corpus with 60 retrieval and 50 routing queries, froze topic-grouped dev/test splits, and compared Dense, BM25 and RRF Hybrid; Hybrid reached 97.5% Recall@3 on a 24-query synthetic retrieval test with documented ranking trade-offs.
- Selected routing instructions on dev only; the frozen configuration routed 20/20 synthetic test queries correctly, while retaining the 15/20 baseline and a negative Tool Description-only result.
- Compared Direct, Always Retrieve and Agent Routing, separating routing from final-answer quality; Agent Routing avoided 5/5 unnecessary retrieval cases in a 20-query synthetic test but did not dominate answer accuracy or end-to-end latency.

## B. 面试可讲

### 60 秒项目介绍

我做的是一个本地 Agentic RAG 项目。nanobot 提供 Agent runtime，两份 MIT 项目提供部分 RAG 基础，我主要做组件适配、统一 Retriever、只读外部工具和分层实验。Qwen 通过 Ollama 自主决定是否查库，证据以 role=tool 返回后再生成答案。V0.2 先冻结 40 个虚构资料块和 dev/test，再比较 Dense、BM25、Hybrid、路由配置及三种检索策略。实验里 Hybrid 的证据覆盖更好，但 BM25 的 MRR 更高；路由能做到这 20 条 synthetic test 全对，最终答案仍只有 14 条严格正确。它避免了 5 次不必要检索，却没有降低本地推理总耗时。我还保留了固定相似度阈值的负结果，没有为了指标好看改题或调 test。这些是小样本工程实验，不是生产可靠性证明。

### 适合展开的结论

1. **为什么不能只报一个 RAG accuracy？** Routing 20/20、final 14/20：检索证据不足、改写退化、角色/事实类型混淆及 generation 错误在后续层，不能都算 Router 错。
2. **Hybrid 是否全面更好？** Test Recall@3 97.5%，BM25 MRR@3 0.8917 高于 Hybrid 0.8750；coverage 和首个相关排名优化的是不同目标。默认 Tool 仍 Dense。
3. **Agent 是否优于 Always Retrieve？** 本次 strict Direct 7/20、Always Retrieve 15/20、Agent Routing 14/20；Agent 避免 5/5 无需检索题、没有 missed retrieval，但没有全面提升答案质量。
4. **为什么减少 Tool 不一定更快？** B1 固定策略无需规划 LLM，B2 通常两次 LLM；retrieval 约 0.2s，小模型规划成本远大于它。E2E mean 31.13/50.06/71.93s 来自不同时段与调用成本，不能普遍外推。
5. **为什么没有采用 threshold？** Dev 选 0.85 后 test 仅检出 1/4 no-answer、误拒 11/20 answerable；最高 no-answer similarity 约 0.8961，只匹配实体而不证明属性存在。负结果限定当前语料/embedding。
6. **如何避免 test 泄漏？** 主题组 split 与 hash freeze；dev 预注册选择，test 后不调 Prompt/阈值、改答案或删除失败题。人工模板偏差、历史部分结果已见的限制仍诚实披露。
7. **哪些工作原创？** 复用 nanobot AgentRunner/ToolRegistry 和 MIT RAG 基础；项目完成归属清晰的改编、插件接口、冻结评估、对照/消融与 bad-case 分析，保留 upstream commit/license。

A1 dev 76.67% 低于 A0 83.33%，A2 96.67%：描述更长不自动有效。该观察值得讲，但不声称 instruction 的普遍因果规律。Threshold 负结果适合面试，不必放简历主 bullet。

## C. 不建议宣传

- “生产级 Agent”“大规模 benchmark”“perfect/generalizable 100% router”或不注明 20-query synthetic 的 100%。
- “Hybrid 全面领先/显著提升”；“Agent Routing 提升最终答案准确率/降低 latency”。
- “固定阈值 universally useless”或“解决幻觉”；本实验只分析 Dense score，不新增 Evidence Judge。
- “从零原创 nanobot/完整 RAG 框架”；不隐去 MIT 改编与 runtime 依赖。
- 已接入默认 Hybrid、A2 instruction、Reranker、MCP、Memory、LangGraph、Multi-Agent、GraphRAG 等未采用能力。
- 把 234 validation/test checks 当 234 条模型 benchmark：真实口径为 220 pytest、11 plugin verification、3 independent metric checks。

[完整实验总结](v0.2/V0_2_SUMMARY.md) · [公开证据](v0.2/evidence/) · [第三方归属](../THIRD_PARTY_NOTICES.md)
