# Phase 1.5 — Dataset Quality Audit

结论：本轮静态逐条审阅未发现阻断 checkpoint 的明显 dev/test 私有事实或答案组合泄漏；存在下列设计 warning。没有修改任何 corpus、query、标签、split 或 hash manifest，没有运行 V0.2 模型 benchmark。

审阅覆盖两个数据集的全部 110 条问题和全部 40 块；以下按要求展示 14 条 Retrieval 代表样本（2/2/2/3/3/2）。这是单一审阅流程，不是第三方人工盲评或语义泄漏的数学证明。

## 14 条代表样本

### v2-r-013 · exact_keyword · dev

- Query：归档箱 ARC-TF 对应报销的提交期限是多少天？
- expected_chunk_ids：`travel_deadline.txt:ptxt:000`
- Evidence 摘要：TR-10F 的现场报销必须在返程后 21 天内提交，归档箱编号 ARC-TF。票据核验角色为角色 T-33，核验不等于审批。
- 类别依据：精确唯一编号 ARC-TF，需要找到该归档箱对应的报销时限。
- 答案泄漏：未提供答案 21 天。
- 是否过于简单：较简单：编号唯一、答案直接在短文中。
- 实质重复审阅：与 v2-r-017 共享现场报销期限这一子事实，同属 dev；不是整题重复。

### v2-r-025 · exact_keyword · test

- Query：系统 SV-18B 的模型归档保留多少天？
- expected_chunk_ids：`sable18b_model.txt:ptxt:000`
- Evidence 摘要：服务器 SABLE-18B 保存模型权重，模型归档保留 180 天，角色为角色 S-33。系统编号 SV-18B，与访问审计无关。
- 类别依据：精确系统编号 SV-18B，目标是模型归档期限，而非备份期限。
- 答案泄漏：未提供答案 180 天。
- 是否过于简单：较简单：编号唯一；仍需辨别归档与备份。
- 实质重复审阅：v2-a-022 引用同一块但问管理角色，字段不同，同属 test。

### v2-r-002 · semantic_paraphrase · test

- Query：Aurora 新一年度的值守工作由谁统筹，何时开始轮值？
- expected_chunk_ids：`aurora_roster.txt:ptxt:000`
- Evidence 摘要：Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。
- 类别依据：值守“统筹”对应名册中的项目负责人，同时询问轮值起始日，包含轻度语义改写。
- 答案泄漏：未提供负责人或日期。
- 是否过于简单：偏简单：仍保留 Aurora 名字，语义改写幅度有限。
- 实质重复审阅：v2-a-003 复用负责人子事实并增加审批角色，同属 test。

### v2-r-044 · semantic_paraphrase · dev

- Query：申请普通小额购买时，一笔最多多少元，需要几份不同商家的报价？
- expected_chunk_ids：`proc_small.txt:ptxt:000`
- Evidence 摘要：政策 PC-21 针对小额采购，单笔上限 12000 元，审批角色为角色 P-11，须留 2 家报价。它不处理设备资本支出。
- 类别依据：“普通小额购买”“不同商家的报价”对应小额采购政策，不直接给出 PC-21 编号。
- 答案泄漏：未提供 12000 元或 2 家报价。
- 是否过于简单：中低难度：关键词依旧明显，但需同时取额度与报价数量。
- 实质重复审阅：v2-a-037 单问同一额度，是同属 dev 的部分事实重复。

### v2-r-009 · entity_ambiguity · test

- Query：Borealis-2 的正式上线日期是哪天？
- expected_chunk_ids：`borealis2_schedule.txt:ptxt:000`
- Evidence 摘要：Borealis-2 编号 B2-620，正式上线定于 2028 年 6 月 20 日。上线负责人是角色 B-22，不沿用 Borealis 的演示日期。
- 类别依据：Borealis 与 Borealis-2 的演示/上线不同，正确目标是后者正式上线日期。
- 答案泄漏：未提供日期。
- 是否过于简单：较简单：后缀与“正式上线”已明确目标。
- 实质重复审阅：v2-a-008 的两日期组合复用此子事实，同属 test。

### v2-r-033 · entity_ambiguity · dev

- Query：ORBIT-3A 的会议预约由哪个角色受理？
- expected_chunk_ids：`orbit3a_reservation.txt:ptxt:000`
- Evidence 摘要：ORBIT-3A 的预约角色是角色 M-44，工作日开放 08:30 至 17:30。维护申请提前 2 个工作日提交。
- 类别依据：ORBIT-3A 与 ORBIT-3 的预约角色不同，不能抹掉后缀 A。
- 答案泄漏：未提供角色 M-44。
- 是否过于简单：较简单：实体名和职责都显式。
- 实质重复审阅：v2-a-028 问两会议室开放时段而非角色，不是同一事实。

### v2-r-022 · hard_negative · dev

- Query：RX-41R3 验收要连续运行多久，而不是 R2 的 36 小时？
- expected_chunk_ids：`robot_r3_acceptance.txt:ptxt:000`
- Evidence 摘要：RX-41R3 的载荷试验为 24 千克，验收角色是角色 R-44，连续运行 60 小时。18 千克标准仅属于 RX-41R2。
- 类别依据：RX-41R3 与 R2 都有验收连续运行要求，但分别为 60/36 小时。
- 答案泄漏：目标 60 小时未泄露；query 已给出反例 36 小时，是难度提示。
- 是否过于简单：偏简单：主动排除反例，比自然模糊问题更容易。
- 实质重复审阅：v2-a-017 问 R3 载荷、v2-r-023 问 R2 时长，字段或实体不同。

### v2-r-028 · hard_negative · test

- Query：SABLE-18B 的备份保留多久，不是模型归档的 180 天？
- expected_chunk_ids：`sable18b_backup.txt:ptxt:000`
- Evidence 摘要：SABLE-18B 的模型备份于每天 04:00 执行，备份保留 30 天，角色为角色 S-44。不能用 SABLE-18 的备份窗口替代。
- 类别依据：同为 SABLE-18B，备份保留 30 天与模型归档保留 180 天不同。
- 答案泄漏：目标 30 天未泄露；反例 180 天给出后降低了判别难度。
- 是否过于简单：偏简单：资料类型和反例都明确，不应未经实测称为困难样本。
- 实质重复审阅：v2-a-025 问备份开始时间，引用同块但不是同一事实。

### v2-r-046 · hard_negative · dev

- Query：CAB-21C 的归档角色是谁，不是 PC-21C 的审批角色？
- expected_chunk_ids：`proc_capital_archive.txt:ptxt:000`
- Evidence 摘要：PC-21C 设备采购单保存 365 天，归档柜编号 CAB-21C，角色为角色 P-44。归档角色无权代替采购审批。
- 类别依据：同一 PC-21C，采购审批 P-22 与 CAB-21C 归档 P-44 是不同职责。
- 答案泄漏：未给 P-44，但明确说不是审批角色，是类别提示。
- 是否过于简单：偏简单：角色区分与柜编号都明确。
- 实质重复审阅：v2-r-045 问审批角色，答案不同；不是同一事实重复。

### v2-r-005 · multi_evidence · test

- Query：列出 Aurora 的值守统筹人、年度预算，以及 Aurora-X 的采购上限。
- expected_chunk_ids：`aurora_roster.txt:ptxt:000`, `aurora_finance.txt:ptxt:000`, `aurora_x_finance.txt:ptxt:000`
- Evidence 摘要：Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。；Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。；Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。
- 类别依据：负责人、年度预算、另一项目采购上限分别来自三块，三条缺一不可。
- 答案泄漏：没有给出角色或金额；实体/字段不算答案。
- 是否过于简单：组合难度高于单事实，但不需深层推导。
- 实质重复审阅：与 v2-r-001/002/004、v2-a-003/005 部分事实重叠，全部在 test。

### v2-r-017 · multi_evidence · dev

- Query：现场保障出差的住宿封顶额度、提交期限和票据核验角色分别是什么？
- expected_chunk_ids：`travel_field.txt:ptxt:000`, `travel_deadline.txt:ptxt:000`
- Evidence 摘要：内部政策 TR-10F 用于现场保障差旅，住宿上限每晚 680 元。审批角色是角色 T-22，普通 TR-10 的额度不能套用。；TR-10F 的现场报销必须在返程后 21 天内提交，归档箱编号 ARC-TF。票据核验角色为角色 T-33，核验不等于审批。
- 类别依据：现场住宿上限在 travel_field，提交期限与核验角色在 travel_deadline，需要两块。
- 答案泄漏：没有给 680 元、21 天或 T-33。
- 是否过于简单：需要证据拼接，事实仍直述；不涉及跨页/长文。
- 实质重复审阅：与 v2-r-013/015 的子事实重叠，同属 dev。

### v2-r-041 · multi_evidence · dev

- Query：列出 Cedar 演示冻结日期和 Cedar-Lite 内容冻结、正式发布日期。
- expected_chunk_ids：`cedar_demo.txt:ptxt:000`, `cedar_lite_freeze.txt:ptxt:000`, `cedar_lite_release.txt:ptxt:000`
- Evidence 摘要：Cedar 的内部演示版本在 2028 年 7 月 3 日冻结，演示角色为角色 C-11，版本号 CE-D08。冻结不是正式发布日期。；Cedar-Lite 的内容冻结日为 2028 年 8 月 2 日，冻结角色为角色 C-44。冻结至正式发布之间不安排新内容合入。；Cedar-Lite 的正式发布定于 2028 年 8 月 16 日，发布角色为角色 C-22，版本号 CL-R08，属于精简版。
- 类别依据：Cedar 演示冻结与 Cedar-Lite 冻结/发布是三个不同事件，来自三块。
- 答案泄漏：没有给出三个日期。
- 是否过于简单：需三块覆盖与事件配对，仍是显式短文事实。
- 实质重复审阅：同属 dev 的 v2-r-038/040 复用部分日期；非跨 split 重复。

### v2-r-030 · no_answer · test

- Query：SABLE-18B 的磁盘总容量是多少 TB？
- expected_chunk_ids：[]
- Evidence 摘要：无支持目标属性的资料。SABLE-18B 仅有模型/备份保留期等记录。
- 类别依据：SABLE-18B 文档只有归档/备份角色、时刻和保留期，全库未记录该机磁盘 TB 容量。
- 答案泄漏：没有答案可泄露；不能把天数当容量。
- 是否过于简单：拒答逻辑清晰；没有实测模型是否会编造，不能声称已很难。
- 实质重复审阅：其他 no-answer 涉及不同实体/属性，共享缺失信息任务模板，不是同一事实。

### v2-r-036 · no_answer · dev

- Query：ORBIT-3 最多可以容纳多少人？
- expected_chunk_ids：[]
- Evidence 摘要：无支持目标属性的资料。ORBIT-3A 为 26 人；不能推给 ORBIT-3。
- 类别依据：只有 ORBIT-3A 有 26 人，ORBIT-3 的人数缺失；相似实体不能互相补全。
- 答案泄漏：未提供 ORBIT-3 人数，也未把 26 人写进 query。
- 是否过于简单：比普通不存在实体更有混淆性，但仍为受控短文场景。
- 实质重复审阅：v2-a-029 与 v2-a-030 实质询问同一缺失容量，三条全部在 dev；必须记录重复权重。

## Dev/Test 语义审阅 A–D

- A：六个 dev 主题组与四个 test 主题组不交叉；有答案证据 chunk 的交集为空。逐条比较实体/版本/属性后，未发现同一私有事实仅换问法跨 split。chunk ID 不同本身不构成证明，已另检查含义与角色/时限单位。
- B：所有非空 expected_chunk_ids 的集合在两个 split 之间没有完全相同组合；multi-evidence 组合未跨 split 重复。空集合 no-answer 不能据此算答案重复。
- C：任务模板可以迁移，但从 dev 轻微换实体不能直接得到 test 的真实角色/日期/数值。例如 dev v2-r-042（Cedar-Lite 年度授权价格）与 test v2-r-012（Borealis-2 销售价）都缺价格；这是缺失属性设计的共享偏差，不是同一实体事实。dev v2-r-020（R2 保养）与 test v2-r-006（RX-41 电池容量）共享编号前缀，却不是同型号/同属性。
- D：十个 hard_negative query 都有“而非/不是/不能”等显式区别。不是仅制造同文档 query 换词：corpus 中确有不同实体/角色/时间对象对应不同值。但措辞本身已告诉模型排除哪个对象，应标为已提示的对照负例，不能宣称测到了自然模糊场景能力。

## Warning 列表（不自动修数据）

1. **同 split 的事实重复权重**：v2-r-036 / v2-a-029 / v2-a-030 均询问 ORBIT-3 缺失容量（dev）；v2-r-055 / v2-a-050 均含 DUTY-7 的 20 分钟升级条件（test）；v2-r-056 / v2-a-047 均含起始日期（test）。未来按 suite 分开统计，不能把 110 条当 110 个独立事实样本。
2. **共享问法/缺失属性先验**：v2-r-042(dev)、v2-r-012(test)、v2-a-019(dev) 分别问不同对象价格，均无答案；相似任务模板与统一缺失属性可能让拒答偏容易。不能从这次审阅声称完全无设计泄漏或自然分布泛化。
3. **反例提示**：v2-r-022(dev)给了36小时、v2-r-028(test)给了180天，均不是目标答案，但帮助排除；v2-r-046(dev)显式区分审批/归档。保留原题，不据此改 test。
4. **编码规律**：角色 A/B/R/P 等前缀及 11/22/33/44 后缀有人工规律（如 v2-r-046 的 P-44、v2-a-007 的 B-22）；不能证明模型一定要检索才能猜中角色。职责映射并非全库统一，但仍有合成 shortcut 风险。
5. **别名假设**：v2-r-020 用“第二版 RX-41”指 RX-41R2，文档没有明确解释 R2 是第二版；该 semantic_paraphrase 的约定可能让标注边界偏宽，不自动修题。
6. **Routing 强提示**：例如 v2-a-016(dev)只做算术、v2-a-001(test)不查内部项目，general_no_tool 明确限制范围；这不是完全不提示工具使用的自然用户分布。
7. **V0.1/V0.2 语境**：v2-a-003 的 Aurora 项目负责人是2028值守名册角色A-11，V0.1 是另一历史名册。只允许独立 corpus 实验，不能混库后仍沿用本 golden。
8. **人工已接触 test**：作者/本轮审阅者看过完整 test，用于质量审计而非调参。此冻结不是秘密 blind holdout；后续须按锁定协议评测，不据审阅样本调 Prompt。

没有把 warning 重新解释成已测得的模型 bad case；没有明显直接泄漏，故可建立受限用途 checkpoint。若用户认为上述人工先验不可接受，应另行批准新数据版本，不能修改已冻结版本的题目来改善后续指标。

## Corpus 难度统计

- 字符数（Python len，含标点）：min 54 / max 79 / mean 64.025 / median 64.0 / p95 77.1。
- cl100k_base tokens：min 46 / max 67 / mean 55.2 / median 55.0 / p95 62.1；40–49 有4块，50–59 有28块，60–69 有8块。仅切块计量，不是 Qwen/nomic tokenizer。
- 主要肯定事实共121条：2条/块有5块，3条/块有29块，4条/块有6块。按人工式正面实体-属性断言计数，不按句号；否定/澄清/重复背景不另计，日期与时间区间各算一个事实。此数字是审阅口径，不是事实抽取模型指标。
- 相似实体/政策编号10组：Aurora系、Borealis系、TR系、RX系、SABLE系、ORBIT系、Cedar系、PC系、LOG系、DUTY系。其中项目/设备/服务器/场地/产品主实体6组，政策/流程编号4组；不是任意相似词 pair 的数量。
- 相似职责10个主题组：项目/审批/验收；发布/验收；差旅审批/票据核验；维护/验收；审计/备份/归档；预约/维护；演示/冻结/发布；审批/归档；审计/导出审批/备份；一线/二线/升级/演练。
- 数字/日期混淆10个主题组：预算/采购上限，演示/上线日期与48/84小时，住宿/补贴额度与报销期限，载荷/运行小时，审计/归档/备份天数，开放/维护时刻与人数缺失，冻结/发布日期，采购金额/报价数/归档天数，生产/测试/备份保留时间，一线/二线/升级/演练分钟。
- hard_negative类别10题/10组，metadata标注30个 query正例chunk→候选负例chunk 对；这只是候选对，未通过模型验证 hardness。另逐题确认10个主要混淆对，见下段。
- Retrieval multi-evidence：8题需2块、2题需3块；Routing private_multi_evidence：10题需2块，没有>2块。
- **40 documents → 40 chunks 属于 controlled synthetic retrieval benchmark，不代表长文档 chunking 性能。** 最长67个计量token，未触发160窗口拆分，也不验证overlap边界、OCR、表格或跨页证据。

### 十个主要负例关系

- v2-r-004：Aurora-X采购上限 vs Aurora年度预算。
- v2-r-010：BT-7B/Borealis-2签字角色 vs BT-7/Borealis签字角色。
- v2-r-016：TR-11培训补贴 vs TR-10住宿报销。
- v2-r-022：RX-41R3的60小时 vs RX-41R2的36小时。
- v2-r-028：SABLE-18B备份30天 vs 模型归档180天。
- v2-r-034：ORBIT-3网络维护窗口 vs 开放时段。
- v2-r-040：Cedar-Lite内容冻结日 vs 正式发布日期。
- v2-r-046：PC-21C归档角色 vs 采购审批角色。
- v2-r-052：生产审计导出审批 vs 审计管理。
- v2-r-058：DUTY-8演练5分钟 vs DUTY-7真实响应15分钟。

### 每块主要事实数与审阅依据

- `aurora_finance.txt:ptxt:000`：3条；2028 年预算为 186000 元；财务审批负责人是角色 A-33；政策编号 FIN-A12。
- `aurora_roster.txt:ptxt:000`：3条；项目编号为 AU-812；项目负责人是角色 A-11；2028 年 3 月 6 日。
- `aurora_x_acceptance.txt:ptxt:000`：4条；项目编号 AX-812；验收负责人为角色 A-22；验收设备是 RX-41；连续运行 96 小时。
- `aurora_x_finance.txt:ptxt:000`：4条；预算为 216000 元；审批负责人是角色 A-44；政策编号 FIN-AX12；采购上限为 32000 元。
- `borealis2_acceptance.txt:ptxt:000`：3条；验收设备 BT-7B；连跑 84 小时；角色 B-44。
- `borealis2_schedule.txt:ptxt:000`：3条；编号 B2-620；2028 年 6 月 20 日；角色 B-22。
- `borealis_acceptance.txt:ptxt:000`：4条；角色 B-33；设备 BT-7；连跑 48 小时；验收签字必须早于内部演示。
- `borealis_schedule.txt:ptxt:000`：3条；项目编号 BO-620；发布负责人是角色 B-11；2028 年 5 月 12 日。
- `cedar_demo.txt:ptxt:000`：3条；2028 年 7 月 3 日；角色 C-11；版本号 CE-D08。
- `cedar_lite_freeze.txt:ptxt:000`：3条；2028 年 8 月 2 日；角色 C-44；冻结至正式发布之间不安排新内容合入。
- `cedar_lite_release.txt:ptxt:000`：3条；2028 年 8 月 16 日；角色 C-22；版本号 CL-R08。
- `cedar_release.txt:ptxt:000`：3条；2028 年 9 月 4 日；角色 C-33；版本号 CE-R09。
- `duty_escalation.txt:ptxt:000`：3条；未响应满 20 分钟；角色 D-33；归档号 INC-707。
- `duty_l1.txt:ptxt:000`：3条；角色 D-11；响应期限 15 分钟；2028 年 10 月 1 日。
- `duty_l2.txt:ptxt:000`：2条；响应期限 45 分钟；角色 D-22。
- `duty_training.txt:ptxt:000`：3条；角色 D-44；每月 8 日；响应目标 5 分钟。
- `orbit3_network.txt:ptxt:000`：2条；每周五 18:30 至 19:30；角色 M-33。
- `orbit3_reservation.txt:ptxt:000`：3条；预约角色为角色 M-11；09:00 至 18:00；场地编号 RM-003。
- `orbit3a_capacity.txt:ptxt:000`：3条；最多容纳 26 人；场地编号 RM-03A；2 台投影仪。
- `orbit3a_reservation.txt:ptxt:000`：3条；角色 M-44；08:30 至 17:30；提前 2 个工作日。
- `proc_capital.txt:ptxt:000`：3条；单笔上限 75000 元；角色 P-22；3 家报价。
- `proc_capital_archive.txt:ptxt:000`：3条；保存 365 天；编号 CAB-21C；角色 P-44。
- `proc_small.txt:ptxt:000`：3条；单笔上限 12000 元；角色 P-11；2 家报价。
- `proc_small_archive.txt:ptxt:000`：4条；保存 90 天；编号 CAB-21；角色 P-33；报价单与审批单一起归档。
- `ret_access.txt:ptxt:000`：2条；角色 L-33；批准后 4 小时内。
- `ret_backup.txt:ptxt:000`：3条；保留 28 天；角色 L-44；编号 BK-032。
- `ret_prod.txt:ptxt:000`：3条；保留 120 天；角色 L-11；每次导出需记录用途。
- `ret_test.txt:ptxt:000`：2条；保留 7 天；角色 L-22。
- `robot_r2_acceptance.txt:ptxt:000`：3条；角色 R-22；18 千克；连续运行 36 小时。
- `robot_r2_service.txt:ptxt:000`：3条；角色 R-11；每周二 10 点；登记号为 MA-412。
- `robot_r3_acceptance.txt:ptxt:000`：3条；24 千克；角色 R-44；连续运行 60 小时。
- `robot_r3_service.txt:ptxt:000`：3条；角色 R-33；每周四 15 点；登记号 MA-413。
- `sable18_audit.txt:ptxt:000`：4条；访问审计记录；保留 60 天；角色 S-11；系统编号 SV-180。
- `sable18_backup.txt:ptxt:000`：3条；每天 02:30；角色 S-22；备份保留 14 天。
- `sable18b_backup.txt:ptxt:000`：3条；每天 04:00；保留 30 天；角色 S-44。
- `sable18b_model.txt:ptxt:000`：4条；模型权重；保留 180 天；角色 S-33；系统编号 SV-18B。
- `travel_deadline.txt:ptxt:000`：3条；返程后 21 天内；编号 ARC-TF；角色 T-33。
- `travel_field.txt:ptxt:000`：2条；住宿上限每晚 680 元；角色 T-22。
- `travel_standard.txt:ptxt:000`：3条；每晚 480 元；角色 T-11；返程后 14 天内。
- `travel_training.txt:ptxt:000`：3条；培训补贴；每日上限 300 元；角色 T-44。

## Hash manifest 覆盖与冻结

现有 freeze_manifest.json 已包含40份corpus原文、corpus_manifest、dataset_config、retrieval_golden、agent_routing_golden、split_manifest，共45文件。两个 golden 文件都包含 dev 与 test，所以全文件hash覆盖四个分区；无需再复制成四个数据文件或建立第二套hash机制。
清单本身SHA256 `078b30d94d2c4664a30aece15b3c255c9351345edc40a02dca15213b9fae9d18`，与Phase1一致。测试ID同时由split_manifest和frozen_test_ids确认。
冻结说明见 DATASET_FREEZE.md；本审计只记录观察，不修改清单或标签。

## 回归计数

V0.1 historical regression scope: 51 =37 original pytest +11 plugin verification +3 independent routing metric checks。Phase0.5首次只执行前两部分，48是执行子集，不是另一完整历史口径。
V0.2 current full validation scope: 91 =上述51 +40 dataset validation。重复运行不增加独立测试数，Phase1.5没有新增测试或算法。
Phase 1.5 checkpoint 前实际复核：77项pytest（37原有 +40dataset，JUnit记录26.133秒）、11项plugin verification、3项独立metric checks全部通过，共91项检查。dataset schema/hash校验通过；25项V0.1 frozen hash、索引/metadata及Phase2/3A/3B evidence均未改变，nanobot仓库clean。不运行V0.2模型benchmark。
