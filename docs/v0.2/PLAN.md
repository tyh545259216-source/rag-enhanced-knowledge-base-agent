# V0.2 Phase 0 — Audit 与实施计划

状态：仅完成审计与计划，尚未实现、运行或调优 V0.2 实验。

本轮只新增本文件，并创建 `feat/v0.2-eval-hybrid` 分支。本文的指标均引用冻结历史记录，不能作为当前机器重新运行的结果。后续实施需要用户确认。

## Phase 1 范围更新（最新用户要求）

Phase 1 已按新要求建立独立 40 文档/40 chunks 的 V0.2 corpus、60 retrieval 与 50 routing 问题，均按主题组 dev/test=60%/40%。权威文件与真实 91 项回归结果见 [DATASET_REPORT.md](DATASET_REPORT.md)。

这替代下文 Phase 0 初始计划中“沿用 9 块、60 题/20 dev/40 test”的建议；该建议仅保留为当时的规划记录。V0.1 的 9 块与所有 baseline 不变。新 corpus 特意放在 eval/v0.2/corpus/，避免 V0.1 Loader 递归读取 data/ 时混入新资料。

本阶段只准备数据与校验，未实现后续算法或调 Prompt。后续 Retrieval 对照应基于这个新 corpus 单独构建 V0.2 索引并重新预注册候选配置，不能直接沿用下文针对 9 块写下的候选池假设，也不能把旧指标和新 corpus 的结果直接视为效果提升。

## 1. 当前架构与审计范围

### 1.1 仓库状态与版本

- 审计开始前：`main`，working tree clean，与 `origin/main` 同步。
- 当前 HEAD：`24f6f49f7cf6de68c1d9af5bcb1326cbb16d7e68`。
- V0.1 tag：`v0.1-agentic-rag-baseline`，目标 `aa422d826fa484933d9949c16fc79e1a2f22eda1`。
- 新分支：`feat/v0.2-eval-hybrid`，从上述 HEAD 创建；未 amend、commit 或 push。
- 相邻 nanobot：commit `66f5f2df15455b34fc22e656bdc1ef3d4f32e328`，工作区 clean；distribution 版本 0.3.5。
- 当前相邻虚拟环境 Python 实测 3.12.14；项目仍声明 Python >=3.11。
- Ollama 当前只读检查：版本 0.35.1；模型列表存在 `qwen3:1.7b`（ID `8f68893c685c`）和 `nomic-embed-text:latest`（ID `0a109f422b47`）。本轮未执行推理或 embedding。
- RAG 上游：`rag-from-scratch` commit `4c4e039177ce2a7ac475339cff7a1187a6fd68bf`；`ollama-local-rag-demo` commit `2d4a5d30b4a4829a007b8132e11cea71282a83d7`，出处继续遵循现有 THIRD_PARTY_NOTICES。

### 1.2 当前调用链

```text
PDF/TXT → extractor → fixed chunker → Ollama embedding + L2 normalization
→ FAISS IndexFlatIP + metadata → RAGAdapter → Retriever.search()
→ SearchKnowledgeBaseTool → nanobot external entry point / ToolRegistry
→ AgentRunner → Qwen structured tool_calls → role=tool → Qwen final answer
```

已检查以下实际实现，而非假设项目行为：

- `src/knowledge_base_agent/vendor/rag_core/extractor.py`：PyMuPDF 按页提取 PDF，跳过空页，保留数字；TXT 使用 UTF-8；目录遍历与 source 相对路径。
- `vendor/rag_core/chunker.py`：fixed chunking；验证 chunk_size/overlap；保存 source/page/块序号。当前配置 size=160、overlap=24。`cl100k_base` 仅用于切块计量，不是 Qwen/nomic 的真实 tokenizer。
- `vendor/ollama_embeddings.py`：document/query 使用相同模型，调用 Ollama `/api/embeddings`；真实返回值确定维度；检查 NaN/Inf/零向量并 L2 normalize。
- `vendor/rag_core/faiss_store.py`：`IndexFlatIP` 精确检索；向量归一化后 inner product 对应余弦相似度，分数越大越相似；K 超过索引数量时裁剪。
- `rag/adapter.py`：入库、加载、query embedding、FAISS 搜索、metadata 转换；记录 embedding/FAISS/total latency。
- `rag/retriever.py`：`search(query: str, top_k: int = 3) -> list[SearchResult]`；非空 query、正整数 K；不生成答案、不添加 threshold。
- `rag/schemas.py`：统一 Document、Chunk、SearchResult；结果包含 text/source/chunk_id/score/page。
- `tools/search_knowledge_base.py`：read-only 外部 Tool；只调用 Retriever；使用锁与线程转交阻塞检索；不会调用 Qwen。
- 相邻 nanobot 的 `nanobot/agent/runner.py`、`nanobot/agent/tools/registry.py`、`nanobot/agent/tools/execution.py`：真实 AgentRunner、prepare_call、execute_tool_calls、ToolResult 和 role=tool 传递。

### 1.3 Corpus、索引与 metadata

当前 `data/` 包含 9 份虚构内部 TXT，持久化后为 9 个 chunk、9 个唯一 chunk_id、page 均为 null。没有大型语料或 PDF 检索评测证据。

- note_01：Aurora 项目负责人林澈、代号 AU-731、发布日期。
- note_02：Aurora 验收负责人周岚、RB-204、72 小时验收要求。
- note_03：Aurora 预算 128000 元、审批人顾宁、采购限制。
- note_04：Borealis 项目负责人、代号、发布日期。
- note_05：RB-204 维护负责人及时间。
- note_06：SABLE-17 保存 Aurora 验收日志，保留 45 天。
- note_07：Cedar 发布资料。
- note_08：NORTH-6 服务器管理与盘点资料。
- note_09：ORBIT-3 会议室预约负责人、开放时间；没有容量资料。

现有索引为 768 维 `IndexFlatIP`，ntotal=9，metadata count=9。

审计实测 `store/index_info.json` SHA256：
`ea6994f07dffaf49c06ef78c7a9c30a00e04c45700bf4ca0cd3b875803e45f72`，与 retrieval golden 绑定值一致。

index_info 中的 index SHA256 为 `04ba1c866a0a533e04706bf381b68c90f879b68c11aefbe2fc78bb0b604c6a77`，metadata SHA256 为 `b282a5bf4cecb377dacd196fe5a58056272928db462a7849ef5a65e55c86b93a`。后续实验还要逐一校验实际文件，不能仅相信清单中的值。

### 1.4 当前 Tool / Prompt 契约

Tool 名称 `search_knowledge_base`；query 为必填 string、minLength=1；top_k 为 integer、默认 3、minimum=1、maximum=10；禁止额外参数。返回 rank/text/source/chunk_id/score/page，不加阈值。

当前描述：

> Search the local internal knowledge base. Return evidence with sources and scores, not a final answer. Nearest neighbors may not answer the question.

Phase 3B 通用 instruction：

> 你可以使用提供的工具完成用户任务。当回答依赖本地私有知识库的信息时，可以调用 search_knowledge_base 获取相关证据。如果工具结果不足以支持答案，请明确说明无法确定。

当前评测隔离使用单个知识库工具，并非包含全部 nanobot 工具的多工具路由评测。V0.2 继续相同边界，不新增 Memory。

## 2. 当前冻结 baseline 与 bad cases

来源：`docs/EVALUATION.md`、`docs/BAD_CASES.md`、`eval/`、`docs/evidence/phase3b/`。这里是历史结果摘要，不重新计算或替换原结果。

### 2.1 Retrieval

30 题：20 有答案（15 单块、5 多块）+10 无答案；按已知语料编题，不是独立 holdout。

- K=1：HitRate 0.85、Recall 0.75、MRR 0.85。
- K=3：HitRate 1.0、Recall 0.975、MRR 0.925。
- K=5：HitRate 1.0、Recall 1.0、MRR 0.925。
- 无答案不参与 HitRate/Recall/MRR，不把空相关集合 Recall 记为 1。
- 30 题各 3 次，共 90 次检索；一次 Top5 后截断为不同 K，不是各 K 独立延迟实验。
- 总检索 mean 151.950 ms、median 138.886 ms、p95 252.149 ms；embedding mean 151.650 ms，FAISS mean 0.281 ms。
- 有答案 Top1：n=20，0.772871–0.892266；无答案：n=10，0.601635–0.867672。明显重叠，不能把 score 当概率或据此上线拍脑袋阈值。

### 2.2 Routing 与最终答案

24 题，general_no_tool/private_single_fact/private_multi_evidence/private_no_answer 各 6 题。

- TP=15，FP=0，FN=3，TN=6。
- Accuracy=87.50%，Precision=100%，Recall=83.33%，F1=90.91%。
- 类别 routing：general 6/6、single 6/6、multi 5/6、no-answer 4/6。
- 15 次 structured tool call 参数有效、role=tool ID 对应正确；39 次 LLM 请求 HTTP 200。
- 15 次 query rewrite 保留意图；11 道有答案问题的证据覆盖未改善/未降级；4 道无答案问题仍然无答案，不代表排序逐项相同。
- 私有问题 18 题：core correctness 16/18=88.89%，strict groundedness 15/18=83.33%。
- 有答案 evidence complete 11/12；已检索问题 11/11。
- 无答案 abstention 6/6=100%，但“先检索再拒答”仅 4/6=66.67%。
- 严格幻觉：无答案 2/6、所有私有题 3/18；无答案目标事实编造 0/6。严格口径包含虚假检索声明和不准确证据概括，不能混用口径。
- 无工具 E2E n=9：mean/median/p95=25.816/21.191/53.695 秒。
- 有工具 E2E n=15：58.530/56.890/70.063 秒。
- 有工具 LLM1 mean=25.786 秒，retrieval tool mean≈0.248 秒，LLM2 mean=32.338 秒。

小语料、人工编题/判读、单模型、单工具、单轮历史实验。上述指标不能外推生产、大规模、多工具或未知文档。

### 2.3 需要保留的失败与边界

- “项目负责人”与“验收负责人”：q01 正确负责人位于 Top2；r07 检索证据正确，但生成端误判为矛盾。分开记录 retrieval 排名与 evidence interpretation。
- 多证据 q20：预算证据未进入 Top3，部分 recall；r17 多证据问题没有检索而反问背景，属于 routing。
- r20：未检索却声称“知识库未找到”，属于 routing + provenance。
- r22：密码问题被直接安全拒答，按冻结 golden 仍记 FN，另注明 policy boundary，不事后改标签。
- r23：正确拒答容量，但错误概括结果只谈其他项目，忽略返回的 ORBIT-3 资料，属于 generation。
- q28：no-answer Top1 高达约 0.867672；高相似度不等于包含答案。
- 当前没有实际出现 general false positive 或 query rewrite 降级，不制造这些 bad case。

## 3. V0.2 预计新增/修改文件与实施边界

采用独立实验目录，保留原生产检索与 Tool。下列为待批准的文件草案，不表示本轮已创建代码；实施时可合并小文件，避免过度封装。

### 3.1 新增文件

- `experiments/v0_2/__init__.py`：实验包。
- `experiments/v0_2/retrieval.py`：BM25、确定性词法 tokenizer、RRF Hybrid；复用冻结 Retriever 和 metadata，保存各分支 rank/score。
- `experiments/v0_2/datasets.py`：schema、group split、证据 ID/数据完整性校验。
- `experiments/v0_2/metrics.py`：routing、retrieval、answer、no-answer、分位数与分母校验。
- `experiments/v0_2/agent_eval.py`：真实 AgentRunner A/B 实验、限定工具、观测、超时、原始响应记录；不创建另一套 Agent loop。
- `experiments/v0_2/reporting.py`：run manifest、checkpoint、JSON→Markdown、冻结文件校验。
- `scripts/v0_2/evaluate_retrieval.py`、`evaluate_routing.py`、`run_ablation.py`：独立 CLI，明确配置文件及输出目录。
- `eval/v0_2/retrieval_golden.json`、`agent_routing_golden.json`、`split_manifest.json`：新题与预注册划分；不替换 V0.1 文件。
- `eval/v0_2/configs/retrieval.yaml`、`routing_ab.yaml`、`ablation.yaml`：固定参数、模型、重复数、seed、timeouts、prompt/schema hash、数据版本。
- `tests/v0_2/`：词法/BM25/RRF、数据划分、指标、报告恢复、Agent 观测与只读保护测试；另有明确标记的真实集成测试。
- `docs/v0.2/`：新增运行/协议说明、独立实验报告、bad cases；本 PLAN 先完成。

所有新功能必须同时具备测试、正式命令、实验配置、原始 JSON 和 Markdown 报告。不能只有示例 notebook 或手工表格。

### 3.2 可能修改的既有非核心文件

后续仅在必要时给 README 增加 V0.2 独立运行入口；若现有 artifacts 忽略规则不足，可补精确 .gitignore。当前不需要改变 pyproject 的 Python 范围或新增依赖；优先标准库实现小规模 BM25。

默认 config、Tool entry point、Retriever API、已有启动脚本与持久化格式保持不变。Hybrid 先做离线 sidecar 对照，不替换 SearchKnowledgeBaseTool 的核心行为。

## 4. 绝对不修改的文件与保护措施

- `v0.1-agentic-rag-baseline` 及其目标 commit，不移动/删除/重建，不 amend/force push。
- `src/knowledge_base_agent/` 全部现有 RAG、vendor、Embedding 和 Tool 实现。
- `data/`、`store/index.faiss`、`store/metadata.json`、`store/index_info.json`、默认 `config.yaml`。
- `eval/` 中既有 golden、baseline、search results、正式旧脚本与原始指标。
- `docs/evidence/phase2/`、`phase3a/`、`phase3b/`、现有 audit/release/evaluation/bad-case 历史记录。
- 已有 tests、licenses、THIRD_PARTY_NOTICES 与 nanobot core/Provider。

Phase 0 已检查 `docs/releases/frozen_core.json` 的 25 项：存在且 SHA256 一致；上述三份 evidence、旧 eval/data 相对 V0.1 tag 没有 Git diff。此清单未覆盖所有目录，所以未来另增加实验输出中的扩展只读清单，覆盖核心、数据、索引、全部历史证据和 tag。

每次实验前后记录文件 SHA256、Git HEAD/tag、nanobot commit/dirty 状态；发现变化立即标记 invalid run 并停止，不静默恢复文件或替换历史产物。

严禁调用会覆盖原 baseline 的 legacy `eval/baseline.py` 作为 V0.2 入口。现有 `scripts/evaluate_retrieval.py` 是安全复核入口，其结果也不能改名充当 V0.2 新实验或覆盖历史报告。

## 5. 数据集设计与评估协议

### 5.1 分开历史回放与新数据

V0.1 的 30 道 retrieval / 24 道 routing 只做独立 historical diagnostic replay，结果注明“已看过的旧样本”，不能宣称 holdout，也不与新测试混成一个提升数字。

V0.2 第一版计划 60 道新问题，四类各 15 道：general_no_tool、private_single_fact、private_multi_evidence、private_no_answer。general 的 expected_tool=null；三类 private 的 expected_tool=search_knowledge_base。

目标划分 dev 20（每类 5）、sealed test 40（每类 10），固定 seed=42。按 entity/property/evidence-set/同义改写意图建立 family_id 做 group split，不能把同一题的改写分到两边。若组大小导致无法精确平衡，运行前记录实际划分，不为了结果再调比例。

仍使用相同 9 个 chunk：这是 query holdout，不是未知 corpus 泛化。撰题者已经看过 V0.1 结果，应明确人工设计偏差。新题不照抄旧题后改一两个词。

### 5.2 每题 schema

保存 id、question、category、family_id、split、expected_tool、answerable、expected_answer、relevant_chunk_ids、required_facts/evidence_groups、acceptable_abstention、annotation_basis。

区分“全部相关资料”与“回答必需事实”，多证据既报 macro Recall 又报 all-required-evidence completion。相关集合为空只用于 no-answer 分析，不制造完美 recall。

容量、保留时间、负责人等缺失私有事实是 no-answer 主集合；安全密码/凭证类可另列 policy challenge，不能与普通 no-answer 混淆。旧 r22 仍按原标签保留。

数据/标签/划分在首次模型运行前锁定哈希；每题保留至报告，无删失败题、改答案或事后选取最好重复结果。发现真实标注错误只能建立有说明的新版本，旧结果留存且不能作为同一次无变化比较。

### 5.3 指标与分母

- Retrieval：answerable 的 HitRate@1/3/5、macro Recall@1/3/5、MRR@1/3/5、multi-evidence completion；明确相关集合与 duplicate ID 处理。
- Routing：TP/FP/FN/TN、Accuracy/Precision/Recall/F1、各类别、参数有效率、unexpected tool、structured call 与纯文本声明的区别。
- Answer：core correctness、strict groundedness、false provenance、policy refusal、target-fact fabrication；private/general 的分母分别报告。
- 无工具时请求数按实际记录；多次/并行工具或第三轮请求不能强行折成“2 次”。
- API/超时/传输失败保留每题记录，报告 attempted/completed/coverage 和全样本 task success；routing metrics 对有可判定模型决策的样本计算并标出未判定题，不能把连接失败冒充 FN 或默默剔除。
- 无有效分母显示 N/A，不填 0 或 100%；mean/median/p95 使用统一定义并单测。
- answer 判读先保留不可编辑的 raw 输出，再生成独立 judgments，写明判断理由和 rubric。评测摘要从 raw+judgments 重算，不手工编辑输出指标；人工判读尽量隐藏 A/B 标签，不用另一个新 LLM 作 judge。

## 6. BM25 / Hybrid 设计

### 6.1 共同输入与 Dense 对照

全部方法使用相同冻结 chunk 文本、ID、source/page、query 和 K。Dense 直接调用现有 Retriever，原始 FAISS 顺序不改。当前 N=9，小规模精确对照，无 ANN、增量写入或新索引覆盖。

embedding/query 模型仍为 nomic-embed-text，不能给某一方法偷偷增补事实、关键词或文档。Dense 候选取 min(10,N)，BM25 取同一上限，fusion 后取 K；当前等于全库 9 个候选。记录候选配置，未来扩库需要新实验版本。

### 6.2 词法 tokenizer 与 BM25

标准库可复现实现，固定 tokenizer_version：拉丁文本小写；字母/数字/带连字符内部编号保留整词；数字保留；连续中文段取相邻双字 token，单字段保留单字。记录标点处理、query 重复词处理（首版 query token 去重）和空 token 行为。

不使用 tiktoken 充当中文语义分词，不新增按测试答案编写的同义词表/stopword 列表。中文双字只是透明的最小词法基线，不承诺最佳中文检索。

固定 BM25：k1=1.5、b=0.75，正 IDF `log(1 + (N-df+0.5)/(df+0.5))`，文档长度与平均长度按上述 token 数计算；参数在看 sealed test 前锁定，本轮不调参。

没有任何词法命中时返回空候选，并记录 zero_lexical_match；不把任意零分文档填成有用证据，也不把空 BM25 结果直接判定成知识库无答案。这是词法候选规则，不是语义 score threshold。

### 6.3 Reciprocal Rank Fusion

Hybrid 使用等权 RRF：`rrf_score(d) = sum(1 / (60 + rank_method(d)))`，rank 从 1 开始，常数 60 预注册。按 chunk_id 合并、去重；某分支无该 chunk 则不贡献；同分只对新融合结果采用稳定 chunk_id tie-break。

不能直接加 BM25 原始分数和 cosine score。输出 score_kind、dense_score/dense_rank、bm25_score/bm25_rank、rrf_score 与最终 rank。RRF 分数不是 cosine，不可套用旧 no-answer score 范围。

BM25 全空时 Hybrid 仅有 Dense 排名贡献，明确记录 fallback；不修改 Dense 原始结果或 Tool 返回协议。实验结果结构放在 sidecar，现有 SearchResult 不加字段。

### 6.4 实验表与成本

同题 Dense / BM25 / Hybrid，K=1/3/5；统一候选池后截断，明确不同 K 不是独立推理计时。另记录 BM25 tokenizer/搜索、query embedding、FAISS、fusion 与 total。

真实 embedding 必须由 Ollama 返回；单元测试可用构造向量验证数学，但不据此宣称真实模型成功。先做可复现检索差异和逐题证据分析，不预设 Hybrid 一定优于 Dense。

算法来源：[Stanford IR Book — BM25](https://nlp.stanford.edu/IR-book/html/htmledition/okapi-bm25-a-non-binary-model-1.html)；[Cormack 等，SIGIR 2009 RRF 原论文](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf)。具体 tokenizer、参数与实验限制是本项目预注册设计，论文不是本项目效果证据。

## 7. Routing A/B 设计

### 7.1 只改变一个变量

A：原 Phase 3B 通用 instruction + 原 Tool description。

B：保持同一 instruction、schema、Retriever、Provider、模型参数，只在实验进程中的 Tool 描述包装层提供一般性证据契约；不修改真实 SearchKnowledgeBaseTool 源文件或注册 entry point。包装层委托原工具执行，不改 query、排序、返回内容或错误行为。

拟预注册 B 描述：

> Retrieves evidence from the local private knowledge base. Use it for questions that depend on that knowledge base, including checks for missing information. Returned passages are evidence candidates, not verified answers; state uncertainty when they do not support an answer.

该描述不包含 Aurora、ORBIT-3、负责人答案、具体测试题或“本轮必须调用工具”。它是通用接口表述实验，不是根据 test bad case 迭代的 Prompt 优化。批准后在新 sealed test 运行前冻结文字/hash；第一轮不做候选筛选或针对测试题调词。

### 7.2 真实执行与安全

新 nanobot 进程真实发现 external entry point；实验隔离注册当前只读工具，仍经过 AgentRunner → OpenAICompatProvider → Ollama → structured tool_calls → ToolRegistry.prepare_call → execute_tool_calls → 原 Tool/原 Retriever → role=tool → 下一轮 Qwen。

不得 Python if/else 决定调用与否，不手写 tool_calls，不用 forced case 代替 routing 指标。不执行 nanobot 其他文件/系统工具，不写长期 Memory，不触发 compaction。

同一 case 新会话/context，固定模型 qwen3:1.7b、localhost Ollama Endpoint、相同 schema/K 默认与迭代上限。记录真实模型参数；Ollama seed 若不被当前接口支持则明确 N/A，不声称跨机器确定性。

A/B 成对测试，交错执行顺序，固定顺序 seed；sealed test 计划每 arm 3 次，报告均值和波动，而非挑最好一次。网络故障按事前规则保存/恢复，不自动多次重试到成功。

### 7.3 记录与 query rewrite

每题保存 model/messages/tools、schema hash、HTTP status、finish_reason、raw/parsed tool_call_id/name/arguments、工具结果、role 序列、最终答案、请求数和分段耗时；不保存 Authorization、API Key、OAuth token、cookie 或用户 Provider 配置。

原 query 与真实工具 query 都保留，离线用相同冻结 Retriever/K 对照 evidence preserved/improved/degraded；字符串不同不是错误。原始 query 的对照检索不参与模型上下文，不能改变这轮答案。

不新增 Query Rewrite 模块。纯文本“我将查询”不是 structured call；多次工具调用保留完整序列和总成本。

## 8. Ablation 设计

按独立轴实施，避免全排列消耗和归因混淆：

1. **检索轴**：Dense-only / BM25-only / RRF Hybrid；相同 corpus、query、K、候选上限，观察命中/覆盖/排名/latency。
2. **K 轴**：1/3/5，针对同一候选排名切片；尤其观察 multi-evidence coverage，不增加 Agent 默认 K。
3. **Routing 描述轴**：A/B 都使用冻结 Dense Tool，先回答“接口描述是否影响自主决策”；不同时把 B 换成 Hybrid。
4. **自然 query rewrite 轴**：原问题 vs 模型实际 query 的离线检索配对，只观察，不植入新的改写逻辑。
5. **层级控制**：同题 retrieval-only 证据充足与 Agent routing/generation 分开评估，识别“检索正确但未调用/理解错”；不把人工 oracle 答案提供给模型。

先不做 chunk_size、Embedding 模型、Prompt 多变量、生成模型、温度调优或 corpus 扩充的 ablation，它们会改变冻结系统或放大实验矩阵。

新增数学/契约测试必须覆盖 BM25 空词/重复词/长度、RRF 合并/缺分支/tie/去重、score 类型、split family 隔离、zero denominator、multi-call trace、工具 ID 对应、异常/超时保存和输出恢复。不写仅镜像实现的无意义测试。

## 9. No-answer、Bad Case 与报告输出

### 9.1 No-answer

分别报告 Dense cosine、BM25 lexical 和 RRF rank score 的 Top1/TopK 分布、分位数、margin、按 known-entity/unknown-entity/属性缺失的子类统计。不同分数尺度不混画同一个阈值。

统计 no-answer routing、检索后 abstention、只 abstention、目标事实编造、false provenance、证据概括错误。高分且资料不含答案必须保留。

本版不设置运行时 threshold。即使观察到分布分离也只能作为后续 dev calibration 假设，不能拿 test 最优切点回填 Retriever。BM25 空命中同样不等价于语料无答案。

### 9.2 Bad cases

所有真实失败逐题给出 Input / Expected / Actual / Evidence / Failed layer / Possible future improvement；区分 Retrieval、Routing、Arguments、Transport、Generation、Policy、Environment。保留没有出现某失败类型的事实，不补造案例。

既有历史案例引用旧 evidence，不编辑原记录；新案例独立保存。判读须同时看完整 ToolResult 与 final answer，避免把“负责人”和“验收负责人”再次混为一谈。

### 9.3 输出与复跑

每次运行使用 `artifacts/v0_2/<run_id>/`：

```text
config.json
manifest.json
frozen_before.json
cases/<case_id>/<arm>/<repeat>.json
judgments.json
metrics.json
REPORT.md
BAD_CASES.md
frozen_after.json
```

run_id 包含 UTC 时间和配置短 hash；已存在且不匹配的目录拒绝覆盖。逐题原子 checkpoint，恢复只处理未完成项，校验数据/config/model/prompt hash；超时/取消保留失败原始状态，后续重跑使用新的 attempt 记录，不擦除第一次失败。

JSON 是原始证据和机器可复算输入，Markdown 从配置/raw/judgments 自动生成；人工判断只进独立 judgments，不改模型输出。需要公开展示时另生成脱敏副本，原始 run 保留在 ignored artifacts；可发布报告的精选证据放 docs/v0.2，不替换 V0.1 evidence。

HTTP 观测必须局限实验进程并 finally 恢复 hook；若流式观测涉及 UTF-8 分片，使用正确增量解码且有测试。当前观察脚本的逐块 errors=replace 是潜在 trace 风险，不据此宣称旧报告已经损坏。

未来正式命令形式为 `scripts/v0_2/... --config ... --output ...`；本阶段未创建这些命令，README 现在不能宣称它们已经可运行。

## 10. 风险、前置条件、预计时间与实施顺序

### 10.1 Phase 0.5 Editable Install / Runtime Provenance

发布脱敏说明（Phase 5）：本节仅将旧/当前 workspace 和仓库之外的本机绝对目录换为通用占位符；迁移事实、时间、版本、命令参数、测试结果与 hash 结论保持原样。原始路径记录保留在本地 ignored 审计材料和历史 commit，不作为安装脚本配置。

本节更新为实际环境验证记录；Phase 0 的其他分析与历史 baseline 不变。Phase 0.5 未实现 V0.2 功能，未运行 Agent benchmark。

**原因与修复前路径**：目录迁移后，nanobot 运行环境中的 knowledge-base-agent 0.1.0 的 `direct_url.json` 和 `.pth` 仍指向 `<old-workspace>/knowledge-base-agent`，该目录已不存在。从仓库目录之外导入得到 `ModuleNotFoundError: No module named 'knowledge_base_agent'`；entry point 元数据存在，但加载失败。因此当时不是成功加载当前源码，也不是已证实加载旧 checkout；风险是残留路径导致导入失败，若旧目录重新出现则可能误加载。

**实际使用的 Python**：`<workspace>/nanobot/.venv/Scripts/python.exe`，Python 3.12.14。没有切换 Python、重建 venv、更新依赖或修改 Provider/OAuth/Ollama/网络。

**已执行的最小修复**：

```powershell
& '<workspace>/nanobot/.venv/Scripts/python.exe' -m pip install --no-deps --disable-pip-version-check -e '<workspace>/knowledge-base-agent'
```

knowledge-base-agent 仍为 0.1.0；安装前后的 97 个已有 distribution 版本完全一致，没有新增常驻 distribution。pip 的隔离构建依赖仅用于构建 editable wheel，没有升级该运行环境的已有依赖。

**修复后的真实 import**：从 `<outside-checkout>`（仓库之外）运行，得到：

- `knowledge_base_agent.__file__ = <workspace>/knowledge-base-agent/src/knowledge_base_agent/__init__.py`。
- 包 `__path__` 指向同一当前仓库的 `src/knowledge_base_agent`。
- editable `direct_url` 解码后为 `file:///<workspace>/knowledge-base-agent`，editable=true。
- `__editable__.knowledge_base_agent-0.1.0.pth` 指向当前仓库 `src`。
- distribution 名为 `knowledge-base-agent`，package 为 `knowledge_base_agent`。
- entry point：`nanobot.tools / search_knowledge_base`，由该 distribution 提供，值为 `knowledge_base_agent.tools.search_knowledge_base:SearchKnowledgeBaseTool`。

这些本机路径只作为本次 provenance 记录，不是项目安装/实验脚本的硬编码配置。

**额外授权后的修复**：用户随后明确授权修复 nanobot editable 路径并补齐当前项目已声明/验证的测试依赖。在同一个 nanobot Python 环境执行：

```powershell
& '<workspace>/nanobot/.venv/Scripts/python.exe' -m pip install --no-deps --disable-pip-version-check -e '<workspace>/nanobot'
& '<workspace>/nanobot/.venv/Scripts/python.exe' -m pip install --no-deps --disable-pip-version-check 'pytest==8.4.2' 'pluggy==1.6.0' 'iniconfig==2.3.0'
```

nanobot 仍为 0.3.5；没有安装其整套 dev extras。pytest 8.4.2 满足 knowledge-base-agent 的 `pytest>=8,<9`，三个新增版本与该项目原测试环境一致。原有 97 个 distribution 版本均未变化；只新增上述三个测试包。没有修改源码、Provider 配置、OAuth 或网络。

**修复后的实际 runtime provenance**：从项目目录之外运行，无临时 PYTHONPATH，得到：

- `sys.executable = <workspace>/nanobot/.venv/Scripts/python.exe`，Python 3.12.14。
- `nanobot.__file__ = <workspace>/nanobot/nanobot/__init__.py`。
- `knowledge_base_agent.__file__ = <workspace>/knowledge-base-agent/src/knowledge_base_agent/__init__.py`。
- 两个 distribution 的 direct_url 解码后均指向上述当前仓库，editable=true。
- `search_knowledge_base` entry point 由 knowledge-base-agent 0.1.0 提供，真实加载的类文件为当前仓库 `src/knowledge_base_agent/tools/search_knowledge_base.py`。

**当前结论**：两套 editable runtime 路径修复完成，真实测试/插件/Tool 验证均通过；Phase 1 的运行环境前置条件已满足。本次没有实现 V0.2 功能、运行完整 Agent Routing benchmark 或重新生成 baseline。

### 10.2 当前测试结果与完整性

同一个 nanobot Python 环境实际执行：

```powershell
& '<workspace>/nanobot/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider
& '<workspace>/nanobot/.venv/Scripts/python.exe' scripts/verify_plugin.py
```

- 当前全部项目 pytest：37 passed，耗时 5.19 秒；包括 35 unit 和 2 个真实 Ollama embedding integration。
- 正式插件验证：11 tests，0 failures、0 errors；entry point discovery、ToolLoader/ToolRegistry 注册、schema、错误处理、冻结 manifest 与真实 direct Registry call 均通过。
- direct query：`项目 Aurora 的负责人是谁？`，默认 top_k=3。原索引排名保持：note_02（验收负责人，score 0.863106）、note_01（项目负责人，0.816885）、note_03（预算，0.793271）；字段与冻结 baseline 一致，score 验证到小数点后 6 位。
- 仅生成 ignored `artifacts/plugin_schema.json`、`plugin_direct_tool_result.json`、`plugin_test_results.json`，没有覆盖 frozen evidence、历史 baseline 或默认索引。
- PyMuPDF 保留上游 fitz 导入的弃用警告仍存在，测试通过；本轮不改源码消除警告。

原有 101 个 knowledge-base-agent tracked 文件、nanobot tracked 文件无 Git diff；25 项 frozen manifest 无变化；实际 index/metadata/index_info 哈希与修复前一致。Phase2/3A/3B evidence 无变化；旧 tag 仍指向原 commit。只更新本 PLAN 的环境前置问题说明。

旧 routing metric 脚本的 3 项测试本轮未执行，因此本次总数为 48（37 pytest +11 plugin），不是历史报告的 51。新 V0.2 测试数量在实现后以实际 collection/pass/fail 报告，不能提前虚构。

### 10.3 主要风险

- 9 个 chunk 存在 ceiling effect，Hybrid 改善空间小，可能退化；无提升同样有效，不追加技术追指标。
- 中文双字/内部编号的词法基线有限；描述 tokenizer 契约，不拿失败题改同义词规则。
- Qwen3:1.7b stochastic routing、速度、thinking/多次调用会影响成本；报告重复分布，不挑结果。
- 旧 benchmark 手工判读有偏差；新 rubric/独立 judgments 明确判断标准与不确定样本。
- 相同 corpus 的 query holdout 仍受已知语料与人工撰题影响；样本小，不能宣称生产泛化。
- 当前两套 editable 路径已修复并通过真实验证；未来再次迁移目录后仍需复查 import/direct_url，不能只依据 distribution 版本判断。
- 本地 HTTP observer 可能拿到 credentials header：只白名单保留允许字段，绝不写原始 header/cookie。

### 10.4 预计运行时间（估计，不是测量）

以历史本机 no-tool mean≈26 秒、tool mean≈59 秒估算，硬件/模型加载/系统负载会改变结果：

- 后续环境核验与现有回归预计约 5–15 分钟，取决于服务和模型加载；本次 Phase 0.5 已完成授权的路径修复及 48 项验证。
- 单次 retrieval 全方法对照：约 1–3 分钟量级（60 题、重复 embedding、warmup 和输出）；BM25/RRF 在 9 块库中主要是毫秒级计算，仍以实际结果为准。
- 3 题 Agent smoke：约 2–5 分钟。
- dev 20 题 ×2 arms ×1 次：约 30–50 分钟。
- sealed test 40 题 ×2 arms ×3 次=240 个 Agent run：估算约 3–5 小时；如果频繁触达每 case 300 秒超时，上界可接近 20 小时，应先 smoke 后决定批次。
- 人工 evidence/answer 判读与报告：约 2–4 小时工作量，另计异常调查；不通过省略失败题节省时间。

无完整 retrieval×routing×K×repeat 的 Agent 全排列。上述时间是范围估算，不承诺性能。

### 10.5 建议实施顺序与验收

1. 环境前置条件已在 Phase 0.5 完成：两套 editable 路径正确，现有 pytest 与插件/direct call 验证成功；开始 Phase 1 前保留此验证记录。
2. 新数据集、rubric、group split 与 A/B 描述/参数预注册，保存 hash；不得先看 sealed test 模型输出再选版本。
3. 实现 sidecar BM25/RRF +纯 Python 单测；读同一 frozen metadata，Dense 原链不变。
4. 跑独立 retrieval baseline 和 ablation，保存全部 raw JSON/Markdown/score 分布/真实 bad cases。
5. 实现实验 AgentRunner 包装和可靠观测；先 3 题 smoke 验证真实 structured calls/role=tool/原 Tool 委托。
6. 执行固定 dev sanity 与 sealed A/B 重复实验；不根据 test 结果调 Prompt 或改题。
7. 分层人工判读、自动复算指标，记录失败类别与置信限制。
8. 最终原有回归、nanobot clean、旧 tag/扩展冻结哈希一致性；仅在用户批准后 commit 新实验材料。

Phase 0 结束条件：本 PLAN 可审阅，Git 只有本新增文档，旧 tag 与核心/历史 evidence 未改变；停止等待确认，不写实验代码。
