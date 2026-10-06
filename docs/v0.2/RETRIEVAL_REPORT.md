# V0.2 Dense / BM25 / Hybrid Retrieval Report

## Experiment setup

- Dataset checkpoint: `0b74d1968893c76b6c29f72af191c7529e74637e`; version: `v0.2-dataset-1`.
- Dataset manifest SHA256: `078b30d94d2c4664a30aece15b3c255c9351345edc40a02dca15213b9fae9d18`.
- CONFIG SHA256: `f1322d1de5aa8d260c6004f874169e37ca1bc6be2e8880bc8319278eb29c0c67`; parameters and implementation were locked after dev and before test.
- Python 3.12.14; Ollama 0.35.1; packages: `{'numpy': '2.5.3', 'faiss-cpu': '1.15.1', 'httpx': '0.28.1', 'tiktoken': '0.14.0', 'knowledge-base-agent': '0.1.0', 'nanobot-ai': '0.3.5'}`.
- Embedding: `nomic-embed-text:latest`; digest: `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`.
- Reused original RAGAdapter / Retriever / Ollama normalization / FAISS. Independent IndexFlatIP: 40 vectors, dimension 768, metadata 40.
- Dev: 36 queries; test: 24 queries (20 answerable +4 no-answer). Each category test n=4.
- Raw JSON, index, provenance, integrity snapshots, warm-up and timings: `artifacts/v0.2/retrieval/phase2_first_20261005/` (ignored).

## Deterministic BM25 tokenizer / formula

- Tokenizer: nfkc-ascii-id-cjk12-v1. NFKC +casefold; ASCII alphanumeric words/integers retained; hyphenated identifiers (ORBIT-3, RB-204, Aurora-X) kept whole. CJK contiguous runs emit each character and every adjacent bigram. Punctuation separates runs. No dictionary, network or query-specific rule.
- For 项目负责人: 项、目、负、责、人、项目、目负、负责、责人.
- IDF(t)=ln(1+(N-df(t)+0.5)/(df(t)+0.5)).
- BM25(d,Q)=Σ IDF(t) · tf(t,d) · (k1+1) / [tf(t,d)+k1·(1-b+b·|d|/avgdl)], summed once per distinct query term.
- Fixed k1=1.5, b=0.75. Document length counts both unigram and bigram tokens. No stopword filter/query-frequency multiplier. Zero-overlap scores are retained (0), ties use chunk_id ascending; they are not positive evidence.

## Hybrid / RRF

- Dense Top20 +BM25 Top20; equal weights; RRF(d)=Σ 1/(60+rank_i(d)); ranks start at 1.
- Missing from a list contributes zero. Final ties use chunk_id ascending. No score addition or threshold.
- Dense scores: normalized inner product (cosine). BM25 scores: lexical relevance. RRF scores: rank fusion. These three numeric scales are incomparable.

## Overall test metrics

| Method | answerable / no-answer | HitRate@1 | HitRate@3 | HitRate@5 | Recall@1 | Recall@3 | Recall@5 | MRR@3 | MRR@5 |
|---|---|---|---|---|---|---|---|---|---|
| dense | 20 / 4 | 12/20 (60.00%) | 18/20 (90.00%) | 19/20 (95.00%) | 0.5250 | 0.8333 | 0.9500 | 0.7333 | 0.7458 |
| bm25 | 20 / 4 | 17/20 (85.00%) | 19/20 (95.00%) | 20/20 (100.00%) | 0.7667 | 0.9000 | 1.0000 | 0.8917 | 0.9042 |
| hybrid | 20 / 4 | 15/20 (75.00%) | 20/20 (100.00%) | 20/20 (100.00%) | 0.6667 | 0.9750 | 1.0000 | 0.8750 | 0.8750 |

Recall is macro-averaged over answerable queries, not micro-averaged over evidence chunks. MRR@K uses the first relevant result within K; no-answer queries are excluded from all three metrics.

## Category comparison

| Category | Method | n (answerable / no-answer) | Hit@1 | Hit@3 | Hit@5 | Recall@1 | Recall@3 | Recall@5 | MRR@3 | MRR@5 |
|---|---|---|---|---|---|---|---|---|---|---|
| entity_ambiguity | dense | 4 / 0 | 3/4 | 4/4 | 4/4 | 0.7500 | 1.0000 | 1.0000 | 0.8333 | 0.8333 |
| entity_ambiguity | bm25 | 4 / 0 | 4/4 | 4/4 | 4/4 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| entity_ambiguity | hybrid | 4 / 0 | 3/4 | 4/4 | 4/4 | 0.7500 | 1.0000 | 1.0000 | 0.8750 | 0.8750 |
| exact_keyword | dense | 4 / 0 | 3/4 | 4/4 | 4/4 | 0.7500 | 1.0000 | 1.0000 | 0.8750 | 0.8750 |
| exact_keyword | bm25 | 4 / 0 | 2/4 | 3/4 | 4/4 | 0.5000 | 0.7500 | 1.0000 | 0.6250 | 0.6875 |
| exact_keyword | hybrid | 4 / 0 | 3/4 | 4/4 | 4/4 | 0.7500 | 1.0000 | 1.0000 | 0.8750 | 0.8750 |
| hard_negative | dense | 4 / 0 | 2/4 | 4/4 | 4/4 | 0.5000 | 1.0000 | 1.0000 | 0.7500 | 0.7500 |
| hard_negative | bm25 | 4 / 0 | 4/4 | 4/4 | 4/4 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| hard_negative | hybrid | 4 / 0 | 4/4 | 4/4 | 4/4 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| multi_evidence | dense | 4 / 0 | 3/4 | 4/4 | 4/4 | 0.3750 | 0.6667 | 1.0000 | 0.8750 | 0.8750 |
| multi_evidence | bm25 | 4 / 0 | 3/4 | 4/4 | 4/4 | 0.3333 | 0.7500 | 1.0000 | 0.8333 | 0.8333 |
| multi_evidence | hybrid | 4 / 0 | 3/4 | 4/4 | 4/4 | 0.3333 | 0.8750 | 1.0000 | 0.8750 | 0.8750 |
| no_answer | dense | 0 / 4 | — | — | — | — | — | — | — | — |
| no_answer | bm25 | 0 / 4 | — | — | — | — | — | — | — | — |
| no_answer | hybrid | 0 / 4 | — | — | — | — | — | — | — | — |
| semantic_paraphrase | dense | 4 / 0 | 1/4 | 2/4 | 3/4 | 0.2500 | 0.5000 | 0.7500 | 0.3333 | 0.3958 |
| semantic_paraphrase | bm25 | 4 / 0 | 4/4 | 4/4 | 4/4 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| semantic_paraphrase | hybrid | 4 / 0 | 2/4 | 4/4 | 4/4 | 0.5000 | 1.0000 | 1.0000 | 0.7500 | 0.7500 |

## Retrieval latency

| Method | samples | mean ms | median ms | p95 ms |
|---|---|---|---|---|
| dense | 72 | 163.071 | 156.300 | 223.925 |
| bm25 | 72 | 0.583 | 0.549 | 1.007 |
| hybrid | 72 | 164.884 | 152.589 | 225.608 |

- Each backend warmed up once before test; every test query repeated 3 times in frozen order. 72 timed searches per method. Warm-ups and index build excluded.
- Dense/Hybrid include a real query embedding on every call; no embedding cache. BM25 is CPU-only. Methods run sequentially in fixed Dense → BM25 → Hybrid order per query/repetition.
- E2E wall time includes tokenization/search/result conversion; component timings preserved in latency_raw.json. p95 uses linear interpolation; these correlated repetitions are not 72 independent questions.
- Local small controlled synthetic benchmark, not a production throughput/SLA benchmark.

## No-answer scores (not a rejection threshold)

| Method / score scale | queries | Top1 mean | median | min | max |
|---|---|---|---|---|---|
| dense / cosine_inner_product | 4 | 0.855635 | 0.868218 | 0.789981 | 0.896122 |
| bm25 / bm25 | 4 | 11.770027 | 9.705452 | 4.943704 | 22.725502 |
| hybrid / rrf | 4 | 0.032399 | 0.032527 | 0.031754 | 0.032787 |

Top-K may still be returned when no fact answers the query. Raw Top5 scores preserved; no threshold, generation or abstention decision is evaluated here.

## Bad cases

Automated candidates use complete evidence coverage at K=3 as 'correct'. Group D means Hybrid Recall@3 is below the better single method; it does not imply every metric is worse. Group F records annotated negatives in Top3 or missing relevant Top1 for ambiguity/hard-negative questions. It is not an LLM judgement.

### A_bm25_correct_dense_wrong

3 test candidates.

**v2-r-005: 列出 Aurora 的值守统筹人、年度预算，以及 Aurora-X 的采购上限。**

Expected: `['aurora_roster.txt:ptxt:000', 'aurora_finance.txt:ptxt:000', 'aurora_x_finance.txt:ptxt:000']`.
Recall@3: `{'dense': 0.6666666666666666, 'bm25': 1.0, 'hybrid': 1.0}`.

dense Top5:

1. `aurora_x_acceptance.txt:ptxt:000` — 0.852459: Aurora-X 项目编号 AX-812，验收负责人为角色 A-22。验收设备是 RX-41，要求连续运行 96 小时。此卡不记录 Aurora 的验收要求。
2. `aurora_x_finance.txt:ptxt:000` — 0.832247: Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。
3. `aurora_finance.txt:ptxt:000` — 0.802176: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。
4. `aurora_roster.txt:ptxt:000` — 0.783952: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
5. `ret_access.txt:ptxt:000` — 0.643806: LOG-31 生产记录的导出审批角色为角色 L-33，批准后 4 小时内允许导出。审计管理角色不能自行批准导出。

bm25 Top5:

1. `aurora_x_finance.txt:ptxt:000` — 29.459240: Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。
2. `aurora_roster.txt:ptxt:000` — 21.282007: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
3. `aurora_finance.txt:ptxt:000` — 14.036201: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。
4. `proc_small.txt:ptxt:000` — 13.048394: 政策 PC-21 针对小额采购，单笔上限 12000 元，审批角色为角色 P-11，须留 2 家报价。它不处理设备资本支出。
5. `proc_capital.txt:ptxt:000` — 11.897894: 政策 PC-21C 针对设备资本采购，单笔上限 75000 元，审批角色为角色 P-22，须留 3 家报价。

hybrid Top5:

1. `aurora_x_finance.txt:ptxt:000` — 0.032522: Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。
2. `aurora_roster.txt:ptxt:000` — 0.031754: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
3. `aurora_finance.txt:ptxt:000` — 0.031746: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。
4. `aurora_x_acceptance.txt:ptxt:000` — 0.031099: Aurora-X 项目编号 AX-812，验收负责人为角色 A-22。验收设备是 RX-41，要求连续运行 96 小时。此卡不记录 Aurora 的验收要求。
5. `proc_small.txt:ptxt:000` — 0.029514: 政策 PC-21 针对小额采购，单笔上限 12000 元，审批角色为角色 P-11，须留 2 家报价。它不处理设备资本支出。

Engineering analysis (hypothesis, not causal proof): inspect exact entity/role/numeric terms and missing evidence in the ranks above. BM25 weights lexical overlap; Dense depends on embedding geometry; RRF rewards agreement in rank and can demote a relevant item when only one method ranks it highly. No query-specific fix was applied.

**v2-r-026: 不带 B 后缀的 SABLE-18 保存什么记录，多久后到期？**

Expected: `['sable18_audit.txt:ptxt:000']`.
Recall@3: `{'dense': 0.0, 'bm25': 1.0, 'hybrid': 1.0}`.

dense Top5:

1. `sable18b_backup.txt:ptxt:000` — 0.872442: SABLE-18B 的模型备份于每天 04:00 执行，备份保留 30 天，角色为角色 S-44。不能用 SABLE-18 的备份窗口替代。
2. `sable18b_model.txt:ptxt:000` — 0.867185: 服务器 SABLE-18B 保存模型权重，模型归档保留 180 天，角色为角色 S-33。系统编号 SV-18B，与访问审计无关。
3. `sable18_backup.txt:ptxt:000` — 0.857054: SABLE-18 的审计备份于每天 02:30 开始，备份角色为角色 S-22。备份保留 14 天，不是在线审计记录的保留时间。
4. `sable18_audit.txt:ptxt:000` — 0.832175: 服务器 SABLE-18 保存的是访问审计记录，保留 60 天，审计角色为角色 S-11。系统编号 SV-180，不保存模型权重。
5. `borealis_acceptance.txt:ptxt:000` — 0.654327: Borealis 由角色 B-33 负责验收，设备 BT-7 连跑 48 小时后提交报告。验收签字必须早于内部演示。

bm25 Top5:

1. `sable18_audit.txt:ptxt:000` — 16.124254: 服务器 SABLE-18 保存的是访问审计记录，保留 60 天，审计角色为角色 S-11。系统编号 SV-180，不保存模型权重。
2. `robot_r2_service.txt:ptxt:000` — 10.993367: 机器人 RX-41R2 的维护角色为角色 R-11，每周二 10 点检查。型号后缀 R2 不可省略，维修登记号为 MA-412。
3. `sable18_backup.txt:ptxt:000` — 9.483424: SABLE-18 的审计备份于每天 02:30 开始，备份角色为角色 S-22。备份保留 14 天，不是在线审计记录的保留时间。
4. `ret_prod.txt:ptxt:000` — 7.837827: 政策 LOG-31 的生产审计记录保留 120 天，审计角色为角色 L-11。每次导出需记录用途，适用对象是生产环境。
5. `ret_backup.txt:ptxt:000` — 7.122441: LOG-32 的生产备份保留 28 天，备份角色为角色 L-44，备份编号 BK-032。它不是 LOG-31 的在线审计记录。

hybrid Top5:

1. `sable18_audit.txt:ptxt:000` — 0.032018: 服务器 SABLE-18 保存的是访问审计记录，保留 60 天，审计角色为角色 S-11。系统编号 SV-180，不保存模型权重。
2. `sable18_backup.txt:ptxt:000` — 0.031746: SABLE-18 的审计备份于每天 02:30 开始，备份角色为角色 S-22。备份保留 14 天，不是在线审计记录的保留时间。
3. `sable18b_model.txt:ptxt:000` — 0.030835: 服务器 SABLE-18B 保存模型权重，模型归档保留 180 天，角色为角色 S-33。系统编号 SV-18B，与访问审计无关。
4. `sable18b_backup.txt:ptxt:000` — 0.030092: SABLE-18B 的模型备份于每天 04:00 执行，备份保留 30 天，角色为角色 S-44。不能用 SABLE-18 的备份窗口替代。
5. `ret_backup.txt:ptxt:000` — 0.029877: LOG-32 的生产备份保留 28 天，备份角色为角色 L-44，备份编号 BK-032。它不是 LOG-31 的在线审计记录。

Engineering analysis (hypothesis, not causal proof): inspect exact entity/role/numeric terms and missing evidence in the ranks above. BM25 weights lexical overlap; Dense depends on embedding geometry; RRF rewards agreement in rank and can demote a relevant item when only one method ranks it highly. No query-specific fix was applied.

### B_dense_correct_bm25_wrong

1 test candidates.

**v2-r-007: BT-7 的连续运行要求及验收签字人是什么？**

Expected: `['borealis_acceptance.txt:ptxt:000']`.
Recall@3: `{'dense': 1.0, 'bm25': 0.0, 'hybrid': 1.0}`.

dense Top5:

1. `borealis2_acceptance.txt:ptxt:000` — 0.743971: Borealis-2 的验收设备 BT-7B 必须连跑 84 小时，由角色 B-44 签字。BT-7 的旧报告不能替代本次验收。
2. `borealis_acceptance.txt:ptxt:000` — 0.728078: Borealis 由角色 B-33 负责验收，设备 BT-7 连跑 48 小时后提交报告。验收签字必须早于内部演示。
3. `duty_escalation.txt:ptxt:000` — 0.722579: DUTY-7 在一线未响应满 20 分钟时升级，升级协调角色是角色 D-33，事件归档号 INC-707。升级不等于二线响应期限。
4. `duty_l1.txt:ptxt:000` — 0.715592: DUTY-7 的一线值班角色为角色 D-11，响应期限 15 分钟。排班起始日 2028 年 10 月 1 日，二线响应另见 DUTY-7B。
5. `duty_training.txt:ptxt:000` — 0.708762: DUTY-8 为桌面演练，角色为角色 D-44，每月 8 日执行。演练响应目标 5 分钟，不用于真实 DUTY-7 事件。

bm25 Top5:

1. `robot_r2_acceptance.txt:ptxt:000` — 45.696735: RX-41R2 的验收角色为角色 R-22，载荷试验要求 18 千克，连续运行 36 小时。维护签字不代替验收签字。
2. `aurora_x_acceptance.txt:ptxt:000` — 37.577579: Aurora-X 项目编号 AX-812，验收负责人为角色 A-22。验收设备是 RX-41，要求连续运行 96 小时。此卡不记录 Aurora 的验收要求。
3. `robot_r3_acceptance.txt:ptxt:000` — 25.103953: RX-41R3 的载荷试验为 24 千克，验收角色是角色 R-44，连续运行 60 小时。18 千克标准仅属于 RX-41R2。
4. `borealis_acceptance.txt:ptxt:000` — 24.075097: Borealis 由角色 B-33 负责验收，设备 BT-7 连跑 48 小时后提交报告。验收签字必须早于内部演示。
5. `borealis2_acceptance.txt:ptxt:000` — 22.200380: Borealis-2 的验收设备 BT-7B 必须连跑 84 小时，由角色 B-44 签字。BT-7 的旧报告不能替代本次验收。

hybrid Top5:

1. `borealis2_acceptance.txt:ptxt:000` — 0.031778: Borealis-2 的验收设备 BT-7B 必须连跑 84 小时，由角色 B-44 签字。BT-7 的旧报告不能替代本次验收。
2. `borealis_acceptance.txt:ptxt:000` — 0.031754: Borealis 由角色 B-33 负责验收，设备 BT-7 连跑 48 小时后提交报告。验收签字必须早于内部演示。
3. `duty_l2.txt:ptxt:000` — 0.030303: DUTY-7B 的二线响应期限 45 分钟，二线角色为角色 D-22。二线不承担一线的 15 分钟响应要求。
4. `borealis_schedule.txt:ptxt:000` — 0.028577: Borealis 项目编号 BO-620，发布负责人是角色 B-11。内部演示定于 2028 年 5 月 12 日，只有演示排期，不代表正式上线。
5. `robot_r3_acceptance.txt:ptxt:000` — 0.028373: RX-41R3 的载荷试验为 24 千克，验收角色是角色 R-44，连续运行 60 小时。18 千克标准仅属于 RX-41R2。

Engineering analysis (hypothesis, not causal proof): inspect exact entity/role/numeric terms and missing evidence in the ranks above. BM25 weights lexical overlap; Dense depends on embedding geometry; RRF rewards agreement in rank and can demote a relevant item when only one method ranks it highly. No query-specific fix was applied.

### C_hybrid_correct_both_wrong

1 test candidates.

**v2-r-029: SABLE-18 的在线记录和备份分别保留多少天，备份几点开始？**

Expected: `['sable18_audit.txt:ptxt:000', 'sable18_backup.txt:ptxt:000']`.
Recall@3: `{'dense': 0.5, 'bm25': 0.5, 'hybrid': 1.0}`.

dense Top5:

1. `sable18_backup.txt:ptxt:000` — 0.908082: SABLE-18 的审计备份于每天 02:30 开始，备份角色为角色 S-22。备份保留 14 天，不是在线审计记录的保留时间。
2. `sable18b_model.txt:ptxt:000` — 0.898341: 服务器 SABLE-18B 保存模型权重，模型归档保留 180 天，角色为角色 S-33。系统编号 SV-18B，与访问审计无关。
3. `sable18b_backup.txt:ptxt:000` — 0.892708: SABLE-18B 的模型备份于每天 04:00 执行，备份保留 30 天，角色为角色 S-44。不能用 SABLE-18 的备份窗口替代。
4. `sable18_audit.txt:ptxt:000` — 0.872559: 服务器 SABLE-18 保存的是访问审计记录，保留 60 天，审计角色为角色 S-11。系统编号 SV-180，不保存模型权重。
5. `proc_capital_archive.txt:ptxt:000` — 0.669145: PC-21C 设备采购单保存 365 天，归档柜编号 CAB-21C，角色为角色 P-44。归档角色无权代替采购审批。

bm25 Top5:

1. `sable18_backup.txt:ptxt:000` — 38.617102: SABLE-18 的审计备份于每天 02:30 开始，备份角色为角色 S-22。备份保留 14 天，不是在线审计记录的保留时间。
2. `ret_backup.txt:ptxt:000` — 32.261460: LOG-32 的生产备份保留 28 天，备份角色为角色 L-44，备份编号 BK-032。它不是 LOG-31 的在线审计记录。
3. `sable18b_backup.txt:ptxt:000` — 20.398632: SABLE-18B 的模型备份于每天 04:00 执行，备份保留 30 天，角色为角色 S-44。不能用 SABLE-18 的备份窗口替代。
4. `sable18_audit.txt:ptxt:000` — 13.852559: 服务器 SABLE-18 保存的是访问审计记录，保留 60 天，审计角色为角色 S-11。系统编号 SV-180，不保存模型权重。
5. `aurora_roster.txt:ptxt:000` — 12.776590: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。

hybrid Top5:

1. `sable18_backup.txt:ptxt:000` — 0.032787: SABLE-18 的审计备份于每天 02:30 开始，备份角色为角色 S-22。备份保留 14 天，不是在线审计记录的保留时间。
2. `sable18b_backup.txt:ptxt:000` — 0.031746: SABLE-18B 的模型备份于每天 04:00 执行，备份保留 30 天，角色为角色 S-44。不能用 SABLE-18 的备份窗口替代。
3. `sable18_audit.txt:ptxt:000` — 0.031250: 服务器 SABLE-18 保存的是访问审计记录，保留 60 天，审计角色为角色 S-11。系统编号 SV-180，不保存模型权重。
4. `sable18b_model.txt:ptxt:000` — 0.030214: 服务器 SABLE-18B 保存模型权重，模型归档保留 180 天，角色为角色 S-33。系统编号 SV-18B，与访问审计无关。
5. `ret_test.txt:ptxt:000` — 0.030077: LOG-31T 的测试审计记录保留 7 天，管理角色为角色 L-22。测试环境不能直接套用生产审计保留时间。

Engineering analysis (hypothesis, not causal proof): inspect exact entity/role/numeric terms and missing evidence in the ranks above. BM25 weights lexical overlap; Dense depends on embedding geometry; RRF rewards agreement in rank and can demote a relevant item when only one method ranks it highly. No query-specific fix was applied.

### D_hybrid_worse_than_best_single

0 test candidates.

No observed case of this type; no invented example.

### E_multi_evidence_coverage_failure

3 test candidates.

**v2-r-005: 列出 Aurora 的值守统筹人、年度预算，以及 Aurora-X 的采购上限。**

Expected: `['aurora_roster.txt:ptxt:000', 'aurora_finance.txt:ptxt:000', 'aurora_x_finance.txt:ptxt:000']`.
Recall@3: `{'dense': 0.6666666666666666, 'bm25': 1.0, 'hybrid': 1.0}`.

dense Top5:

1. `aurora_x_acceptance.txt:ptxt:000` — 0.852459: Aurora-X 项目编号 AX-812，验收负责人为角色 A-22。验收设备是 RX-41，要求连续运行 96 小时。此卡不记录 Aurora 的验收要求。
2. `aurora_x_finance.txt:ptxt:000` — 0.832247: Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。
3. `aurora_finance.txt:ptxt:000` — 0.802176: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。
4. `aurora_roster.txt:ptxt:000` — 0.783952: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
5. `ret_access.txt:ptxt:000` — 0.643806: LOG-31 生产记录的导出审批角色为角色 L-33，批准后 4 小时内允许导出。审计管理角色不能自行批准导出。

bm25 Top5:

1. `aurora_x_finance.txt:ptxt:000` — 29.459240: Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。
2. `aurora_roster.txt:ptxt:000` — 21.282007: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
3. `aurora_finance.txt:ptxt:000` — 14.036201: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。
4. `proc_small.txt:ptxt:000` — 13.048394: 政策 PC-21 针对小额采购，单笔上限 12000 元，审批角色为角色 P-11，须留 2 家报价。它不处理设备资本支出。
5. `proc_capital.txt:ptxt:000` — 11.897894: 政策 PC-21C 针对设备资本采购，单笔上限 75000 元，审批角色为角色 P-22，须留 3 家报价。

hybrid Top5:

1. `aurora_x_finance.txt:ptxt:000` — 0.032522: Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。
2. `aurora_roster.txt:ptxt:000` — 0.031754: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
3. `aurora_finance.txt:ptxt:000` — 0.031746: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。
4. `aurora_x_acceptance.txt:ptxt:000` — 0.031099: Aurora-X 项目编号 AX-812，验收负责人为角色 A-22。验收设备是 RX-41，要求连续运行 96 小时。此卡不记录 Aurora 的验收要求。
5. `proc_small.txt:ptxt:000` — 0.029514: 政策 PC-21 针对小额采购，单笔上限 12000 元，审批角色为角色 P-11，须留 2 家报价。它不处理设备资本支出。

Engineering analysis (hypothesis, not causal proof): inspect exact entity/role/numeric terms and missing evidence in the ranks above. BM25 weights lexical overlap; Dense depends on embedding geometry; RRF rewards agreement in rank and can demote a relevant item when only one method ranks it highly. No query-specific fix was applied.

**v2-r-011: Borealis 的内部演示时间和 Borealis-2 的验收时长分别是多少？**

Expected: `['borealis_schedule.txt:ptxt:000', 'borealis2_acceptance.txt:ptxt:000']`.
Recall@3: `{'dense': 0.5, 'bm25': 0.5, 'hybrid': 0.5}`.

dense Top5:

1. `borealis2_acceptance.txt:ptxt:000` — 0.811599: Borealis-2 的验收设备 BT-7B 必须连跑 84 小时，由角色 B-44 签字。BT-7 的旧报告不能替代本次验收。
2. `borealis2_schedule.txt:ptxt:000` — 0.801589: Borealis-2 编号 B2-620，正式上线定于 2028 年 6 月 20 日。上线负责人是角色 B-22，不沿用 Borealis 的演示日期。
3. `borealis_acceptance.txt:ptxt:000` — 0.776235: Borealis 由角色 B-33 负责验收，设备 BT-7 连跑 48 小时后提交报告。验收签字必须早于内部演示。
4. `borealis_schedule.txt:ptxt:000` — 0.724559: Borealis 项目编号 BO-620，发布负责人是角色 B-11。内部演示定于 2028 年 5 月 12 日，只有演示排期，不代表正式上线。
5. `cedar_demo.txt:ptxt:000` — 0.633756: Cedar 的内部演示版本在 2028 年 7 月 3 日冻结，演示角色为角色 C-11，版本号 CE-D08。冻结不是正式发布日期。

bm25 Top5:

1. `borealis_acceptance.txt:ptxt:000` — 26.363413: Borealis 由角色 B-33 负责验收，设备 BT-7 连跑 48 小时后提交报告。验收签字必须早于内部演示。
2. `cedar_demo.txt:ptxt:000` — 19.622499: Cedar 的内部演示版本在 2028 年 7 月 3 日冻结，演示角色为角色 C-11，版本号 CE-D08。冻结不是正式发布日期。
3. `borealis_schedule.txt:ptxt:000` — 18.782697: Borealis 项目编号 BO-620，发布负责人是角色 B-11。内部演示定于 2028 年 5 月 12 日，只有演示排期，不代表正式上线。
4. `borealis2_acceptance.txt:ptxt:000` — 16.213118: Borealis-2 的验收设备 BT-7B 必须连跑 84 小时，由角色 B-44 签字。BT-7 的旧报告不能替代本次验收。
5. `aurora_x_acceptance.txt:ptxt:000` — 14.184398: Aurora-X 项目编号 AX-812，验收负责人为角色 A-22。验收设备是 RX-41，要求连续运行 96 小时。此卡不记录 Aurora 的验收要求。

hybrid Top5:

1. `borealis_acceptance.txt:ptxt:000` — 0.032266: Borealis 由角色 B-33 负责验收，设备 BT-7 连跑 48 小时后提交报告。验收签字必须早于内部演示。
2. `borealis2_acceptance.txt:ptxt:000` — 0.032018: Borealis-2 的验收设备 BT-7B 必须连跑 84 小时，由角色 B-44 签字。BT-7 的旧报告不能替代本次验收。
3. `cedar_demo.txt:ptxt:000` — 0.031514: Cedar 的内部演示版本在 2028 年 7 月 3 日冻结，演示角色为角色 C-11，版本号 CE-D08。冻结不是正式发布日期。
4. `borealis_schedule.txt:ptxt:000` — 0.031498: Borealis 项目编号 BO-620，发布负责人是角色 B-11。内部演示定于 2028 年 5 月 12 日，只有演示排期，不代表正式上线。
5. `borealis2_schedule.txt:ptxt:000` — 0.031281: Borealis-2 编号 B2-620，正式上线定于 2028 年 6 月 20 日。上线负责人是角色 B-22，不沿用 Borealis 的演示日期。

Engineering analysis (hypothesis, not causal proof): inspect exact entity/role/numeric terms and missing evidence in the ranks above. BM25 weights lexical overlap; Dense depends on embedding geometry; RRF rewards agreement in rank and can demote a relevant item when only one method ranks it highly. No query-specific fix was applied.

### F_entity_or_hard_negative_confusion

8 test candidates.

**v2-r-003: 带 X 后缀的 Aurora 项目需要持续跑多久才算验收完成？**

Expected: `['aurora_x_acceptance.txt:ptxt:000']`.
Recall@3: `{'dense': 1.0, 'bm25': 1.0, 'hybrid': 1.0}`.

dense Top5:

1. `aurora_x_acceptance.txt:ptxt:000` — 0.784913: Aurora-X 项目编号 AX-812，验收负责人为角色 A-22。验收设备是 RX-41，要求连续运行 96 小时。此卡不记录 Aurora 的验收要求。
2. `aurora_x_finance.txt:ptxt:000` — 0.753205: Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。
3. `aurora_finance.txt:ptxt:000` — 0.711116: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。
4. `aurora_roster.txt:ptxt:000` — 0.706786: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
5. `duty_training.txt:ptxt:000` — 0.591039: DUTY-8 为桌面演练，角色为角色 D-44，每月 8 日执行。演练响应目标 5 分钟，不用于真实 DUTY-7 事件。

bm25 Top5:

1. `aurora_x_acceptance.txt:ptxt:000` — 24.161593: Aurora-X 项目编号 AX-812，验收负责人为角色 A-22。验收设备是 RX-41，要求连续运行 96 小时。此卡不记录 Aurora 的验收要求。
2. `robot_r2_acceptance.txt:ptxt:000` — 14.021081: RX-41R2 的验收角色为角色 R-22，载荷试验要求 18 千克，连续运行 36 小时。维护签字不代替验收签字。
3. `borealis_acceptance.txt:ptxt:000` — 13.545452: Borealis 由角色 B-33 负责验收，设备 BT-7 连跑 48 小时后提交报告。验收签字必须早于内部演示。
4. `borealis2_acceptance.txt:ptxt:000` — 12.264751: Borealis-2 的验收设备 BT-7B 必须连跑 84 小时，由角色 B-44 签字。BT-7 的旧报告不能替代本次验收。
5. `aurora_finance.txt:ptxt:000` — 12.052812: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。

hybrid Top5:

1. `aurora_x_acceptance.txt:ptxt:000` — 0.032787: Aurora-X 项目编号 AX-812，验收负责人为角色 A-22。验收设备是 RX-41，要求连续运行 96 小时。此卡不记录 Aurora 的验收要求。
2. `aurora_finance.txt:ptxt:000` — 0.031258: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。
3. `borealis_acceptance.txt:ptxt:000` — 0.030798: Borealis 由角色 B-33 负责验收，设备 BT-7 连跑 48 小时后提交报告。验收签字必须早于内部演示。
4. `aurora_roster.txt:ptxt:000` — 0.030777: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
5. `aurora_x_finance.txt:ptxt:000` — 0.030018: Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。

Engineering analysis (hypothesis, not causal proof): inspect exact entity/role/numeric terms and missing evidence in the ranks above. BM25 weights lexical overlap; Dense depends on embedding geometry; RRF rewards agreement in rank and can demote a relevant item when only one method ranks it highly. No query-specific fix was applied.

**v2-r-004: FIN-AX12 的单笔采购封顶多少，而非 FIN-A12 的年度总预算？**

Expected: `['aurora_x_finance.txt:ptxt:000']`.
Recall@3: `{'dense': 1.0, 'bm25': 1.0, 'hybrid': 1.0}`.

dense Top5:

1. `aurora_finance.txt:ptxt:000` — 0.754697: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。
2. `aurora_x_finance.txt:ptxt:000` — 0.742221: Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。
3. `aurora_roster.txt:ptxt:000` — 0.687403: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
4. `aurora_x_acceptance.txt:ptxt:000` — 0.664120: Aurora-X 项目编号 AX-812，验收负责人为角色 A-22。验收设备是 RX-41，要求连续运行 96 小时。此卡不记录 Aurora 的验收要求。
5. `travel_deadline.txt:ptxt:000` — 0.629318: TR-10F 的现场报销必须在返程后 21 天内提交，归档箱编号 ARC-TF。票据核验角色为角色 T-33，核验不等于审批。

bm25 Top5:

1. `aurora_x_finance.txt:ptxt:000` — 30.791155: Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。
2. `proc_capital.txt:ptxt:000` — 14.137894: 政策 PC-21C 针对设备资本采购，单笔上限 75000 元，审批角色为角色 P-22，须留 3 家报价。
3. `aurora_finance.txt:ptxt:000` — 12.938965: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。
4. `proc_small.txt:ptxt:000` — 12.650130: 政策 PC-21 针对小额采购，单笔上限 12000 元，审批角色为角色 P-11，须留 2 家报价。它不处理设备资本支出。
5. `proc_capital_archive.txt:ptxt:000` — 10.835012: PC-21C 设备采购单保存 365 天，归档柜编号 CAB-21C，角色为角色 P-44。归档角色无权代替采购审批。

hybrid Top5:

1. `aurora_x_finance.txt:ptxt:000` — 0.032522: Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。
2. `aurora_finance.txt:ptxt:000` — 0.032266: Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。
3. `aurora_roster.txt:ptxt:000` — 0.030798: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
4. `proc_small.txt:ptxt:000` — 0.029710: 政策 PC-21 针对小额采购，单笔上限 12000 元，审批角色为角色 P-11，须留 2 家报价。它不处理设备资本支出。
5. `borealis2_schedule.txt:ptxt:000` — 0.028405: Borealis-2 编号 B2-620，正式上线定于 2028 年 6 月 20 日。上线负责人是角色 B-22，不沿用 Borealis 的演示日期。

Engineering analysis (hypothesis, not causal proof): inspect exact entity/role/numeric terms and missing evidence in the ranks above. BM25 weights lexical overlap; Dense depends on embedding geometry; RRF rewards agreement in rank and can demote a relevant item when only one method ranks it highly. No query-specific fix was applied.

## Default pipeline recommendation

Hybrid merits a later, separately approved candidate evaluation because Recall@3 is higher in this test. This alone is insufficient to replace the default pipeline; compare rank quality, latency and generalization on a larger independently authored corpus.

## Limitations / integrity

- Semantic paraphrase test n=4 only: these questions retain entity/lexical anchors; this result does not establish that BM25 is generally better than Dense at semantic paraphrase.
- Small controlled synthetic benchmark: test=24, category=4, answerable=20. A single category hit changes its HitRate by 25 percentage points; report counts, not broad superiority claims.
- 40 documents →40 chunks does not measure long-document chunking, OCR or cross-page retrieval. Handwritten templates, explicit negative clues and regular role identifiers introduce shortcuts. Test family holdout does not remove all design/style leakage.
- Dev is an implementation sanity run, not extensive hyperparameter search. No test-derived tokenizer/parameter changes, no stronger model, no reranker, no default integration.
- First repetition determines metrics; all repeat ranks/scores/timings are retained. Rank-inconsistent queries: dense=0, bm25=0, hybrid=0.
- Runner verified V0.1 25 hashes, V0.2 45 dataset hashes, tag, protected source/evidence/index fingerprints and clean nanobot both before and after. Final regression checks are reported separately.

## Repeat this experiment

Run from the repository with its nanobot venv. Use a new run directory; previous results cannot be overwritten.

```powershell
$python = '../nanobot/.venv/Scripts/python.exe'
$run = 'artifacts/v0.2/retrieval/' + (Get-Date -Format 'yyyyMMddTHHmmss')
& $python scripts/v0_2/run_retrieval.py --stage dev --run-dir $run
# Review dev implementation behavior. CONFIG may be reused only if identical.
& $python scripts/v0_2/run_retrieval.py --stage lock --run-dir $run
& $python scripts/v0_2/run_retrieval.py --stage test --run-dir $run
```

The runner writes an immutable CONFIG/source-hash lock before test and refuses changes/overwrites. It never calls Qwen or AgentRunner. Preserve the first official run even if later runs differ.

## 工程复核：具体差异与排名退化

以下分析基于本次冻结输出和 corpus 原文；事实为保存的排名/词项贡献，机制解释属于工程分析，不是因果实验或LLM裁判。没有修改CONFIG、检索实现或第一次正式结果。

- **v2-r-007 / BT-7**：Dense 正确证据在第2，BM25在第4，Hybrid在第2。BT-7被保留为完整token，失败不是编号拆散。词项复算显示错误 robot_r2_acceptance 得45.696735，正确 borealis_acceptance 得24.075097；正确块的 bt-7 贡献2.893441。错误块匹配连续/运行/签字等18个query terms，而正确块匹配9个。中文 unigram+bigram 的累积贡献压过了单个设备编号，这是当前词项统计的可观察局限；未添加编号加权规则。
- **v2-r-026 / SABLE-18**：Dense将18B的备份与模型归档排在前面，正确访问审计块在第4；BM25和Hybrid都排第1。BM25完整保留sable-18，与sable-18b是不同token；其词项约束可能帮助区分实体，但这里只能观察排名差异，不能据此断言embedding失效原因。
- **v2-r-029 / 两份保留证据**：Dense与BM25都把在线审计块排第4，Top3各只覆盖1/2证据；RRF将其升到第3，覆盖2/2。可以直接由双方rank=4的贡献2/(60+4)=0.03125解释其融合得分。
- **v2-r-011 / Borealis vs Borealis-2**：三方法Top3都只覆盖1/2；Hybrid需要的演示排期块仍在第4。Hybrid HitRate@3=1不代表多证据问题完整可答。
- **v2-r-028 / 备份 vs模型归档**：正确与错误块RRF得分同为0.032522；正确backup在chunk_id字典序上排前，因此本题Top1正确包含tie规则的影响，并不能说明RRF理解了30天与180天的否定关系。

### Hybrid worse than best single：补充排名口径

预注册候选D使用Recall@3，正式test没有该类退化。但若比较MRR@3，则有以下4例；两种口径都保留，不把D=0描述成Hybrid从不更差。

**v2-r-008：最初的 Borealis 安排在哪一天给内部人员看演示，由谁负责发布？**

MRR@3: `{'dense': 0.3333333333333333, 'bm25': 1.0, 'hybrid': 0.5}`。

dense Top5：

- 1. `borealis_acceptance.txt:ptxt:000`，score=0.733307。
- 2. `borealis2_schedule.txt:ptxt:000`，score=0.732551。
- 3. `borealis_schedule.txt:ptxt:000`，score=0.727049。
- 4. `borealis2_acceptance.txt:ptxt:000`，score=0.703683。
- 5. `aurora_finance.txt:ptxt:000`，score=0.649202。

bm25 Top5：

- 1. `borealis_schedule.txt:ptxt:000`，score=29.756911。
- 2. `borealis_acceptance.txt:ptxt:000`，score=22.093583。
- 3. `cedar_demo.txt:ptxt:000`，score=20.965413。
- 4. `cedar_lite_freeze.txt:ptxt:000`，score=16.587576。
- 5. `borealis2_schedule.txt:ptxt:000`，score=16.305535。

hybrid Top5：

- 1. `borealis_acceptance.txt:ptxt:000`，score=0.032522。
- 2. `borealis_schedule.txt:ptxt:000`，score=0.032266。
- 3. `borealis2_schedule.txt:ptxt:000`，score=0.031514。
- 4. `cedar_demo.txt:ptxt:000`，score=0.030579。
- 5. `aurora_finance.txt:ptxt:000`，score=0.030090。

**v2-r-011：Borealis 的内部演示时间和 Borealis-2 的验收时长分别是多少？**

MRR@3: `{'dense': 1.0, 'bm25': 0.3333333333333333, 'hybrid': 0.5}`。

dense Top5：

- 1. `borealis2_acceptance.txt:ptxt:000`，score=0.811599。
- 2. `borealis2_schedule.txt:ptxt:000`，score=0.801589。
- 3. `borealis_acceptance.txt:ptxt:000`，score=0.776235。
- 4. `borealis_schedule.txt:ptxt:000`，score=0.724559。
- 5. `cedar_demo.txt:ptxt:000`，score=0.633756。

bm25 Top5：

- 1. `borealis_acceptance.txt:ptxt:000`，score=26.363413。
- 2. `cedar_demo.txt:ptxt:000`，score=19.622499。
- 3. `borealis_schedule.txt:ptxt:000`，score=18.782697。
- 4. `borealis2_acceptance.txt:ptxt:000`，score=16.213118。
- 5. `aurora_x_acceptance.txt:ptxt:000`，score=14.184398。

hybrid Top5：

- 1. `borealis_acceptance.txt:ptxt:000`，score=0.032266。
- 2. `borealis2_acceptance.txt:ptxt:000`，score=0.032018。
- 3. `cedar_demo.txt:ptxt:000`，score=0.031514。
- 4. `borealis_schedule.txt:ptxt:000`，score=0.031498。
- 5. `borealis2_schedule.txt:ptxt:000`，score=0.031281。

**v2-r-027：SABLE-18 的备份由谁负责，几点开始？**

MRR@3: `{'dense': 0.3333333333333333, 'bm25': 1.0, 'hybrid': 0.5}`。

dense Top5：

- 1. `sable18b_backup.txt:ptxt:000`，score=0.867943。
- 2. `sable18b_model.txt:ptxt:000`，score=0.846171。
- 3. `sable18_backup.txt:ptxt:000`，score=0.841192。
- 4. `sable18_audit.txt:ptxt:000`，score=0.785280。
- 5. `robot_r3_acceptance.txt:ptxt:000`，score=0.649821。

bm25 Top5：

- 1. `sable18_backup.txt:ptxt:000`，score=20.229882。
- 2. `sable18b_backup.txt:ptxt:000`，score=17.300633。
- 3. `aurora_roster.txt:ptxt:000`，score=12.573707。
- 4. `ret_backup.txt:ptxt:000`，score=11.471751。
- 5. `borealis_acceptance.txt:ptxt:000`，score=9.677175。

hybrid Top5：

- 1. `sable18b_backup.txt:ptxt:000`，score=0.032522。
- 2. `sable18_backup.txt:ptxt:000`，score=0.032266。
- 3. `borealis_acceptance.txt:ptxt:000`，score=0.030310。
- 4. `aurora_finance.txt:ptxt:000`，score=0.029857。
- 5. `sable18_audit.txt:ptxt:000`，score=0.028958。

**v2-r-056：正式一线值守从哪天开始，需要在多久内响应？**

MRR@3: `{'dense': 0.0, 'bm25': 1.0, 'hybrid': 0.5}`。

dense Top5：

- 1. `ret_prod.txt:ptxt:000`，score=0.612711。
- 2. `travel_standard.txt:ptxt:000`，score=0.611655。
- 3. `duty_training.txt:ptxt:000`，score=0.610083。
- 4. `ret_access.txt:ptxt:000`，score=0.609921。
- 5. `cedar_lite_freeze.txt:ptxt:000`，score=0.607824。

bm25 Top5：

- 1. `duty_l1.txt:ptxt:000`，score=25.711966。
- 2. `aurora_roster.txt:ptxt:000`，score=20.398423。
- 3. `duty_l2.txt:ptxt:000`，score=20.096111。
- 4. `duty_escalation.txt:ptxt:000`，score=17.354769。
- 5. `sable18_backup.txt:ptxt:000`，score=12.092468。

hybrid Top5：

- 1. `duty_training.txt:ptxt:000`，score=0.029958。
- 2. `duty_l1.txt:ptxt:000`，score=0.029907。
- 3. `ret_prod.txt:ptxt:000`，score=0.029727。
- 4. `cedar_lite_freeze.txt:ptxt:000`，score=0.029670。
- 5. `travel_standard.txt:ptxt:000`，score=0.029643。

v2-r-027中，18B备份的Dense/BM25 rank为1/2，正确18备份为3/1，RRF分别为0.032522与0.032266，因此误实体仍排首位。它覆盖了正确证据却损失首位精度。这说明融合共识不是实体/职责逻辑判断。

候选F包含“有正确证据但同时带入annotated negative”的情况，8个候选不等于8题检索完全失败。

## Final regression and publication boundary

143 checks passed =37 original pytest +40 dataset checks +52 retrieval checks +11 plugin checks +3 independent metric checks。pytest 129项全部通过（包括既有2项真实Embedding集成测试），未新增模型依赖。原有fitz弃用提示仍在，不影响本次结果。

仅新增实验代码、固定CONFIG、测试及本报告。README、简历数字、默认Tool/Retriever均未修改；没有commit或push。本报告不是生产性能声明。建议保留现有默认pipeline，把Hybrid作为后续候选而非立即替换：本次Recall@3更高，但BM25 Hit@1和MRR更高，且类别仅4题、multi-evidence仍有遗漏。

## Phase 2.5 result audit / freeze checkpoint

Audit UTC: 2026-10-05T03:22:22.562999+00:00. No formal retrieval test was rerun; original raw files remain unchanged.

CONFIG SHA256: `f1322d1de5aa8d260c6004f874169e37ca1bc6be2e8880bc8319278eb29c0c67`; dataset manifest SHA256: `078b30d94d2c4664a30aece15b3c255c9351345edc40a02dca15213b9fae9d18`. Lock: 2026-10-05T03:05:53.552129+00:00; test start: 2026-10-05T03:06:11.288835+00:00. CONFIG and all ten source/test file hashes still match.

Committable evidence: [PHASE2_RETRIEVAL.json](evidence/PHASE2_RETRIEVAL.json). It contains summaries, audit calculations and selected original artifact hashes, not raw traces/indexes. Hashes are captured now and do not pretend to be a previously signed manifest.

### Metric audit

20 answerable queries only; no-answer IDs v2-r-006/012/030/060 excluded. HitRate requires any relevant chunk; Recall divides distinct hits by every required chunk; MRR uses the first relevant rank within K. Independent Fraction-based reconstruction matches every saved query, overall and category metric. K=3/5 cutoffs were reviewed.

Random sample seed 20261005 selected two single-evidence and two multi-evidence questions; extra r026 checks a result falling outside K=3. Below are hand-computable fractions from the stored ranks, not new retrieval runs.

**v2-r-025** — required=1; random seed 20261005.

- dense: relevant ranks [1]; K=1: Hit=1, Recall=1/1, RR=1/1; K=3: Hit=1, Recall=1/1, RR=1/1; K=5: Hit=1, Recall=1/1, RR=1/1.
- bm25: relevant ranks [1]; K=1: Hit=1, Recall=1/1, RR=1/1; K=3: Hit=1, Recall=1/1, RR=1/1; K=5: Hit=1, Recall=1/1, RR=1/1.
- hybrid: relevant ranks [1]; K=1: Hit=1, Recall=1/1, RR=1/1; K=3: Hit=1, Recall=1/1, RR=1/1; K=5: Hit=1, Recall=1/1, RR=1/1.

**v2-r-058** — required=1; random seed 20261005.

- dense: relevant ranks [1]; K=1: Hit=1, Recall=1/1, RR=1/1; K=3: Hit=1, Recall=1/1, RR=1/1; K=5: Hit=1, Recall=1/1, RR=1/1.
- bm25: relevant ranks [1]; K=1: Hit=1, Recall=1/1, RR=1/1; K=3: Hit=1, Recall=1/1, RR=1/1; K=5: Hit=1, Recall=1/1, RR=1/1.
- hybrid: relevant ranks [1]; K=1: Hit=1, Recall=1/1, RR=1/1; K=3: Hit=1, Recall=1/1, RR=1/1; K=5: Hit=1, Recall=1/1, RR=1/1.

**v2-r-029** — required=2; random seed 20261005.

- dense: relevant ranks [1, 4]; K=1: Hit=1, Recall=1/2, RR=1/1; K=3: Hit=1, Recall=1/2, RR=1/1; K=5: Hit=1, Recall=2/2, RR=1/1.
- bm25: relevant ranks [1, 4]; K=1: Hit=1, Recall=1/2, RR=1/1; K=3: Hit=1, Recall=1/2, RR=1/1; K=5: Hit=1, Recall=2/2, RR=1/1.
- hybrid: relevant ranks [1, 3]; K=1: Hit=1, Recall=1/2, RR=1/1; K=3: Hit=1, Recall=2/2, RR=1/1; K=5: Hit=1, Recall=2/2, RR=1/1.

**v2-r-011** — required=2; random seed 20261005.

- dense: relevant ranks [1, 4]; K=1: Hit=1, Recall=1/2, RR=1/1; K=3: Hit=1, Recall=1/2, RR=1/1; K=5: Hit=1, Recall=2/2, RR=1/1.
- bm25: relevant ranks [3, 4]; K=1: Hit=0, Recall=0/2, RR=0; K=3: Hit=1, Recall=1/2, RR=1/3; K=5: Hit=1, Recall=2/2, RR=1/3.
- hybrid: relevant ranks [2, 4]; K=1: Hit=0, Recall=0/2, RR=0; K=3: Hit=1, Recall=1/2, RR=1/2; K=5: Hit=1, Recall=2/2, RR=1/2.

**v2-r-026** — required=1; extra cutoff audit.

- dense: relevant ranks [4]; K=1: Hit=0, Recall=0/1, RR=0; K=3: Hit=0, Recall=0/1, RR=0; K=5: Hit=1, Recall=1/1, RR=1/4.
- bm25: relevant ranks [1]; K=1: Hit=1, Recall=1/1, RR=1/1; K=3: Hit=1, Recall=1/1, RR=1/1; K=5: Hit=1, Recall=1/1, RR=1/1.
- hybrid: relevant ranks [1]; K=1: Hit=1, Recall=1/1, RR=1/1; K=3: Hit=1, Recall=1/1, RR=1/1; K=5: Hit=1, Recall=1/1, RR=1/1.

### All four semantic_paraphrase test samples

**v2-r-002: Aurora 新一年度的值守工作由谁统筹，何时开始轮值？**

- Expected `aurora_roster.txt:ptxt:000`: Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
- Shared unique tokens (13): aurora, 值, 值守, 始, 守, 年, 年度, 度, 开, 开始, 的, 轮, 轮值.
- dense relevant rank: `{'aurora_roster.txt:ptxt:000': 1}`.
- bm25 relevant rank: `{'aurora_roster.txt:ptxt:000': 1}`.
- hybrid relevant rank: `{'aurora_roster.txt:ptxt:000': 1}`.
- Engineering assessment: 保留Aurora、年度、值守、轮值、开始；把负责人换为统筹，属于轻度改写，词汇锚点很强。

**v2-r-008: 最初的 Borealis 安排在哪一天给内部人员看演示，由谁负责发布？**

- Expected `borealis_schedule.txt:ptxt:000`: Borealis 项目编号 BO-620，发布负责人是角色 B-11。内部演示定于 2028 年 5 月 12 日，只有演示排期，不代表正式上线。
- Shared unique tokens (15): borealis, 人, 内, 内部, 发, 发布, 布, 排, 演, 演示, 示, 负, 负责, 责, 部.
- dense relevant rank: `{'borealis_schedule.txt:ptxt:000': 3}`.
- bm25 relevant rank: `{'borealis_schedule.txt:ptxt:000': 1}`.
- hybrid relevant rank: `{'borealis_schedule.txt:ptxt:000': 2}`.
- Engineering assessment: 保留Borealis、内部、演示、发布、负责；问句变长但核心短语仍一致，不能代表强语义改写。

**v2-r-026: 不带 B 后缀的 SABLE-18 保存什么记录，多久后到期？**

- Expected `sable18_audit.txt:ptxt:000`: 服务器 SABLE-18 保存的是访问审计记录，保留 60 天，审计角色为角色 S-11。系统编号 SV-180，不保存模型权重。
- Shared unique tokens (9): sable-18, 不, 保, 保存, 存, 录, 的, 记, 记录.
- dense relevant rank: `{'sable18_audit.txt:ptxt:000': 4}`.
- bm25 relevant rank: `{'sable18_audit.txt:ptxt:000': 1}`.
- hybrid relevant rank: `{'sable18_audit.txt:ptxt:000': 1}`.
- Engineering assessment: 显式保留SABLE-18及保存/记录，并给出不带B的实体排除线索；兼具entity ambiguity，主要不是无词汇锚点的改写。

**v2-r-056: 正式一线值守从哪天开始，需要在多久内响应？**

- Expected `duty_l1.txt:ptxt:000`: DUTY-7 的一线值班角色为角色 D-11，响应期限 15 分钟。排班起始日 2028 年 10 月 1 日，二线响应另见 DUTY-7B。
- Shared unique tokens (9): 一, 一线, 值, 响, 响应, 始, 应, 线, 线值.
- dense relevant rank: `{'duty_l1.txt:ptxt:000': '>5; exact rank not saved'}`.
- bm25 relevant rank: `{'duty_l1.txt:ptxt:000': 1}`.
- hybrid relevant rank: `{'duty_l1.txt:ptxt:000': 2}`.
- Engineering assessment: 没有DUTY-7编号，改写了值班/排班起始日/响应期限；比前三题更间接，但仍有一线、响应等区分词，单个样本不能定义强语义集。

This is not a clean test of strong paraphrase with lexical anchors removed. The Dense errors are observed ranks, not proof of their causal origin. Category n=4 cannot support a general BM25-vs-Dense claim. Frozen queries/labels remain unchanged.

### Hybrid trade-off

Compared with dense:

- HitRate@1: +15.00 percentage points.
- Recall@1: +14.17 percentage points.
- HitRate@3: +10.00 percentage points.
- Recall@3: +14.17 percentage points.
- MRR@3: +0.141667.
- HitRate@5: +5.00 percentage points.
- Recall@5: +5.00 percentage points.
- MRR@5: +0.129167.
- Improved: HitRate@1, Recall@1, HitRate@3, Recall@3, MRR@3, HitRate@5, Recall@5, MRR@5; unchanged: none; decreased: none.

Compared with bm25:

- HitRate@1: -10.00 percentage points.
- Recall@1: -10.00 percentage points.
- HitRate@3: +5.00 percentage points.
- Recall@3: +7.50 percentage points.
- MRR@3: -0.016667.
- HitRate@5: +0.00 percentage points.
- Recall@5: +0.00 percentage points.
- MRR@5: -0.029167.
- Improved: HitRate@3, Recall@3; unchanged: HitRate@5, Recall@5; decreased: HitRate@1, Recall@1, MRR@3, MRR@5.

**Hybrid improves Top-K evidence coverage in this benchmark, but does not dominate first-relevant ranking quality.** Hybrid HitRate@3=100%, Recall@3=97.5%; BM25 MRR@3=0.8917 >Hybrid 0.8750. No default pipeline change.

### No-answer evidence for Phase 4

Dense Top1 scores (n=4): mean 0.855635, median 0.868218, p95 0.893147, min 0.789981, max 0.896122. Individual values are preserved in the snapshot. **High similarity does not imply answer existence.** No threshold, rejection policy or model test was introduced.

### Regression scope

Phase 2.5 rerun: 129 pytest +11 plugin verification +3 independent metric checks =143 passed, zero failures. No new test count was invented for the independent audit calculations. Raw experimental data/indexes/timing samples stay ignored; only experiment source/tests/CONFIG/report/summary are eligible for checkpoint commit.
