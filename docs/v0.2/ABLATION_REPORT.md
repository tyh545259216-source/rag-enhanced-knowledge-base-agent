# V0.2 Phase 3B — Agentic RAG Ablation

## Protocol

B0禁用工具；B1固定策略调度真实ToolRegistry/execute_tool_calls后，role=tool交给AgentRunner单次Qwen生成；B2复用Phase3A首次A2。B1的assistant tool_calls是明确策略安排，不是Qwen输出，也不用于证明structured tool calling。
三者冻结A2 system与generation不变。B1原query检索，top_k匹配A2同题实际值；原未检索5题用schema默认3。B1没有规划LLM、生成后不重新检索；B2通常两次LLM。B1/B2的query、上下文/调用数和测量时间不同，不能将差异全归为routing。
先冻结rubric，再运行B0/B1。strict=(correct+correct_abstention)/20；partial不计strict分。错误附加私有事实判incorrect。B0私有漏检索是strategy-imposed；B1多余检索不是工具错误。
Grounded采用实际收到的证据复核，reference-grounded另存；Evidence completeness为required chunks实际覆盖，不是答案是否提到所有事实。no-answer无required chunks记not_applicable。

## Configuration

Rubric hash: `213831181a1f4636e8174484f4553267310e0515bd44d95d6599e8aaa4ac1be8`；config hash: `59f5e8132cb0e7116fbaea3f133a634898434d8c9abfc7334ef9cda87eb7b72a`。

## B0

Strict final: 7/20 (35.00%); counts: {"correct": 5, "partial": 1, "incorrect": 12, "correct_abstention": 2}
- ambiguous_boundary: 1/4
- general_no_tool: 4/4
- private_multi_evidence: 0/4
- private_no_answer: 2/4
- private_single_fact: 0/4
- Tool usage: {"called_cases": 0, "tool_call_rate": 0.0, "unnecessary": 0, "unnecessary_denominator": 5, "unnecessary_rate": 0.0, "missed": 15, "missed_denominator": 15, "missed_rate": 1.0, "total_calls": 0, "average_calls": 0.0}
- Grounded: 13/20; unsupported private claim cases: 7
- Evidence completeness: {"not_applicable": 9, "none": 11}
- No-answer abstention: 2/4
- Multi-evidence complete: 0/4; fully correct answer: 0/4
- e2e_ms: n=20, mean=31132.76, median=26057.44, p95=64435.34 ms
- tool_ms: not_applicable
- llm1_ms: not_applicable
- llm_final_ms: n=20, mean=31063.33, median=26048.48, p95=63272.53 ms
- Model errors: []; actual LLM request count: 20

## B1

Strict final: 15/20 (75.00%); counts: {"correct": 12, "partial": 0, "incorrect": 5, "correct_abstention": 3}
- ambiguous_boundary: 3/4
- general_no_tool: 3/4
- private_multi_evidence: 2/4
- private_no_answer: 3/4
- private_single_fact: 4/4
- Tool usage: {"called_cases": 20, "tool_call_rate": 1.0, "unnecessary": 5, "unnecessary_denominator": 5, "unnecessary_rate": 1.0, "missed": 0, "missed_denominator": 15, "missed_rate": 0.0, "total_calls": 20, "average_calls": 1.0}
- Grounded: 16/20; unsupported private claim cases: 4
- Evidence completeness: {"not_applicable": 9, "complete": 9, "partial": 2}
- No-answer abstention: 3/4
- Multi-evidence complete: 2/4; fully correct answer: 2/4
- e2e_ms: n=20, mean=50055.69, median=46556.66, p95=71946.53 ms
- tool_ms: n=20, mean=208.28, median=155.07, p95=297.64 ms
- llm1_ms: not_applicable
- llm_final_ms: n=20, mean=49786.20, median=46393.42, p95=71708.32 ms
- Model errors: []; actual LLM request count: 20

## B2

Strict final: 14/20 (70.00%); counts: {"correct": 11, "partial": 0, "incorrect": 6, "correct_abstention": 3}
- ambiguous_boundary: 2/4
- general_no_tool: 4/4
- private_multi_evidence: 2/4
- private_no_answer: 3/4
- private_single_fact: 3/4
- Tool usage: {"called_cases": 15, "tool_call_rate": 0.75, "unnecessary": 0, "unnecessary_denominator": 5, "unnecessary_rate": 0.0, "missed": 0, "missed_denominator": 15, "missed_rate": 0.0, "total_calls": 15, "average_calls": 0.75}
- Grounded: 14/20; unsupported private claim cases: 6
- Evidence completeness: {"not_applicable": 9, "complete": 9, "partial": 1, "none": 1}
- No-answer abstention: 3/4
- Multi-evidence complete: 2/4; fully correct answer: 2/4
- e2e_ms: n=20, mean=71928.19, median=76877.44, p95=121261.11 ms
- tool_ms: n=15, mean=222.79, median=208.82, p95=299.73 ms
- llm1_ms: n=15, mean=33796.57, median=32081.07, p95=49994.65 ms
- llm_final_ms: n=20, mean=46390.83, median=43246.89, p95=73945.32 ms
- Model errors: []; actual LLM request count: 35

## Paired Bad Cases

- B0_wrong_B1_B2_correct: v2-a-003, v2-a-004, v2-a-007, v2-a-008, v2-a-009, v2-a-022, v2-a-025, v2-a-047
- B1_wrong_B2_correct: v2-a-046
- B2_wrong_B1_correct: v2-a-002, v2-a-005
- all_wrong: v2-a-023, v2-a-048, v2-a-050
- B2_routing_correct_answer_wrong: v2-a-002, v2-a-005, v2-a-023, v2-a-048, v2-a-049, v2-a-050

### v2-a-002

- Input: 内部验收卡上 AX-812 用的是哪台设备？
- Expected: RX-41
- B0 incorrect: 无法确定AX-812在内部验收卡中具体对应哪台设备，因为相关资料未在知识库中明确记录。建议查阅具体验收文档或联系相关部门获取详细信息。
- Engineering reason: 未给RX-41并声称知识库没有该设备记录，与gold验收卡矛盾。
- Actual evidence IDs:
- B1 correct: 根据内部验收卡信息，AX-812对应的验收设备为 **RX-41**。该设备的验收要求为连续运行96小时，且该卡不记录Aurora项目的验收细节。

**说明**：
1. 搜索结果中明确指出，Aurora-X项目编号AX-812的验收设备为RX-41（来源：`aurora_x_acceptance.txt`）。
2. 其他结果（如AU-812、RX-41R2）涉及不同项目或不同验收要求，与AX-812无直接关联。
- Engineering reason: RX-41与96小时正确，并正确限定不记录的是Aurora而非Aurora-X。
- Actual evidence IDs: aurora_x_acceptance.txt:ptxt:000, aurora_roster.txt:ptxt:000, robot_r2_service.txt:ptxt:000
- B2 incorrect: 根据内部验收卡记录，项目编号为AX-812的设备为**RX-41**。该设备属于Aurora-X项目，验收负责人角色为A-22，且验收要求不记录在该卡中。需注意，AX-812与AU-812为不同项目，前者涉及Aurora-X，后者为2028年年度值守项目。
- Engineering reason: RX-41正确，但把不记录Aurora验收要求误读为AX-812验收要求不记录；该卡实际记录96小时。
- Actual evidence IDs: aurora_x_acceptance.txt:ptxt:000, aurora_roster.txt:ptxt:000, robot_r2_service.txt:ptxt:000

### v2-a-003

- Input: 按内部记录分别给出 Aurora 的项目负责人和财务审批负责人。
- Expected: 项目角色 A-11；审批角色 A-33
- B0 incorrect: 根据内部记录，Aurora项目的项目负责人为**张伟（Chief Technology Officer, CTO）**，财务审批负责人为**李敏（CFO）**。
（注：此信息基于公司内部项目管理表及财务审批流程的公开记录，具体岗位职责可能因公司架构调整而变动。）

**说明**：
1. 项目负责人通常为技术/业务高管，Aurora作为技术项目，其负责人可能涉及技术领导层；
2. 财务审批负责人通常为财务总监或分管财务的高管，具体需结合公司组织架构确认。
若需进一步核实，建议查阅公司内部项目管理数据库或财务审批流程文档。
- Engineering reason: 编造张伟CTO和李敏CFO作为Aurora负责人，并虚构内部项目管理表来源。
- Actual evidence IDs:
- B1 correct: 根据内部记录，Aurora的财务审批负责人为 **角色 A-33**（政策编号 FIN-A12），而项目负责人信息需进一步确认。
- **财务审批负责人**：角色 A-33（依据 `aurora_finance.txt` 中的记录）。
- **项目负责人**：需结合其他资料确认。例如，Aurora 2028 年度值守项目 AU-812 的项目负责人为 **角色 A-11**（依据 `aurora_roster.txt` 中的记录）。

若需更精确的项目负责人信息，需补充相关记录。
- Engineering reason: 虽措辞犹豫，但明确给出Aurora A-11和A-33及对应真实记录，两项核心事实完整。
- Actual evidence IDs: aurora_finance.txt:ptxt:000, aurora_roster.txt:ptxt:000, aurora_x_acceptance.txt:ptxt:000
- B2 correct: 根据内部记录：

1. **项目负责人**：Aurora 2028年度值守项目负责人为角色 **A-11**（项目编号 AU-812，轮值时间 2028年3月6日）。

2. **财务审批负责人**：Aurora 2028年预算财务审批负责人为角色 **A-33**（政策编号 FIN-A12），该角色不担任项目负责人。

注：A-11与A-33为不同角色，分别对应项目管理和财务审批职责。
- Engineering reason: Aurora项目A-11、审批A-33完整且正确，明确职责不同。
- Actual evidence IDs: aurora_finance.txt:ptxt:000, aurora_roster.txt:ptxt:000, aurora_x_acceptance.txt:ptxt:000

### v2-a-005

- Input: 预算这个词是什么意思？请以内部 FIN-A12 批准单的具体额度举例。
- Expected: 可说明预算含义；内部额度为 186000 元
- B0 partial: 预算（Budget）是指组织或个人在一定时期内对收入和支出的计划安排，用于控制资源分配、确保目标实现。在财务语境中，预算通常包括收入预测、支出计划、资金分配等具体内容。

关于您提到的**FIN-A12批准单**，目前未获取到该文件的具体内容（如额度、项目、审批流程等）。因此无法提供该批准单的精确额度数据。建议您查阅FIN-A12批准单的正式文件或联系相关管理部门获取详细信息。若需进一步解释预算概念，可参考通用财务定义：预算是通过量化分析，将未来财务活动进行规划和分配的工具。
- Engineering reason: 预算概念正确，坦承没有FIN-A12额度；所需186000元实例缺失。
- Actual evidence IDs:
- B1 correct: 预算是指为实现特定目标（如项目、活动或部门）而预先确定的财务资源分配计划。根据内部FIN-A12政策，Aurora的2028年预算金额为**186,000元**，该预算由审批负责人A-33批准。此额度适用于相关项目的资金分配，具体执行细节需参照政策文件中的具体条款。
- Engineering reason: 预算定义与FIN-A12的186000元、Aurora审批A-33正确。
- Actual evidence IDs: aurora_finance.txt:ptxt:000, aurora_x_finance.txt:ptxt:000
- B2 incorrect: 预算是指为实现特定目标而预先规划的财务资源分配方案。以内部政策FIN-A12为例，Aurora的2028年预算金额为**186,000元**，审批负责人为角色A-33，该预算用于项目管理相关支出。该政策的单笔采购上限为32,000元（根据Aurora-X的预算数据推测，具体数值可能因政策版本差异而略有不同）。
- Engineering reason: 186000元正确，但将Aurora-X的32000元单笔采购额度推给FIN-A12，跨项目猜测。
- Actual evidence IDs: aurora_finance.txt:ptxt:000, aurora_x_finance.txt:ptxt:000

### v2-a-023

- Input: 按内部卡片比较 SABLE-18 与 SABLE-18B 各自保存什么、保留多久。
- Expected: 访问审计60天；模型权重180天
- B0 incorrect: 根据内部文档中的记录，SABLE-18和SABLE-18B的存储内容及保留期限如下：

1. **SABLE-18**
   - **保存内容**：通常保存日常操作日志、基础配置信息及基础运行数据（如系统状态、设备参数等）。
   - **保留期限**：默认保留**30天**，具体可能根据业务需求调整（如合规要求或系统生命周期管理）。

2. **SABLE-18B**
   - **保存内容**：额外保存高级配置日志、性能监控数据及特定业务场景的定制化数据（如定制化应用日志）。
   - **保留期限**：默认保留**60天**，部分敏感数据可能需根据法规或内部政策延长至**1年**。

**说明**：若需精确数据，需参考具体设备的配置文档或系统管理策略。若无明确记录，以上信息基于通用逻辑推断，实际以官方文档为准。
- Engineering reason: 编造两服务器日志类型和30/60天默认保留期，与访问审计60天/模型180天不符。
- Actual evidence IDs:
- B1 incorrect: 根据内部卡片信息，SABLE-18与SABLE-18B的保存内容及保留时间如下：

### **SABLE-18**
1. **保存内容**
   - **模型权重**：系统编号SV-18，角色S-22，审计备份保留14天（非在线审计记录的保留时间）。
   - **备份策略**：审计备份每日02:30执行，保留14天。

2. **保留时间**
   - 审计备份保留14天。

---

### **SABLE-18B**
1. **保存内容**
   - **模型权重**：系统编号SV-18B，角色S-33，保留180天。
   - **备份策略**：模型备份每日04:00执行，保留30天。

2. **保留时间**
   - 模型权重保留180天。

---

### **说明**
- SABLE-18的审计备份与SABLE-18B的模型权重保留时间存在差异（14天 vs 180天），需根据具体场景区分。
- SABLE-18B的模型备份保留期为30天，与SABLE-18的审计备份保留期（14天）不同，需注意区分。
- Engineering reason: 将SABLE-18审计备份14天作为所问在线审计保留期，并误称保存模型权重；gold是访问审计60天。
- Actual evidence IDs: sable18b_model.txt:ptxt:000, sable18b_backup.txt:ptxt:000, sable18_backup.txt:ptxt:000
- B2 incorrect: 根据内部文档信息：

**SABLE-18B**
- **保存内容**：模型权重（保留180天）
- **保留时间**：模型权重保留180天，备份数据保留30天

**SABLE-18**
- **保存内容**：审计日志（保留14天）
- **保留时间**：审计备份保留14天

注：
1. SABLE-18B的模型权重备份于每日04:00执行，保留30天；
2. SABLE-18的审计备份于每日02:30执行，保留14天。

（数据来源：`sable18b_model.txt`、`sable18b_backup.txt`、`sable18_backup.txt`）
- Engineering reason: SABLE-18B模型180天正确，SABLE-18在线审计保留期误答为备份14天。
- Actual evidence IDs: sable18b_model.txt:ptxt:000, sable18b_backup.txt:ptxt:000, sable18_backup.txt:ptxt:000

### v2-a-046

- Input: 用自己的话解释一线支持和二线支持的通用区别，不查内部值班制度。
- Expected: 一线接收并初步处理，二线处理升级问题
- B0 correct: 一线支持与二线支持的核心区别在于**响应层级和处理复杂度**：

1. **响应层级**：
   一线支持通常针对**日常问题**（如设备故障、简单操作疑问），由基层团队直接处理；
   二线支持则针对**复杂问题**（如系统瘫痪、高级技术需求），需由更高层级团队介入。

2. **处理复杂度**：
   一线支持侧重**即时性**，快速解决简单问题；
   二线支持强调**深度分析**，需排查多层级原因，可能涉及远程诊断或跨部门协作。

3. **资源与时间**：
   一线支持优先级高，响应时间短；
   二线支持耗时较长，资源投入更多，但解决效果更彻底。

总结：一线支持是“快速响应的简单处理”，二线支持是“深度分析的复杂解决”，两者共同目标是保障服务质量，但分工不同。
- Engineering reason: 通用一线快速初步处理与二线复杂升级处理的区别正确。
- Actual evidence IDs:
- B1 incorrect: 根据现有资料，一线支持和二线支持的通用区别无法明确界定，因为搜索结果中未涉及相关术语或定义。建议查阅具体文档或联系相关部门获取详细说明。
- Engineering reason: 把不需要私有证据的通用问题拒答为资料未提供；没有给一线与二线概念区别。
- Actual evidence IDs: duty_l2.txt:ptxt:000, cedar_demo.txt:ptxt:000, proc_small_archive.txt:ptxt:000
- B2 correct: 一线支持通常指直接面向客户或用户，处理即时性、高频的业务需求，例如电话客服、现场服务等，强调快速响应和直接解决问题。而二线支持则可能涉及更复杂的问题或需要跨部门协作的场景，例如技术故障排查、系统升级等，通常由更高层级的资源或团队提供支持。两者的核心区别在于服务层级、问题复杂度及资源调配方式。
- Engineering reason: 一般一线面向用户初步处理、二线处理更复杂升级问题，核心区别正确。
- Actual evidence IDs:

### v2-a-048

- Input: 按照内部资料，一线和二线各由哪个角色值守、分别多久响应？
- Expected: D-11 15分钟；D-22 45分钟
- B0 incorrect: 根据内部资料，一线和二线的值守角色及响应时间可能涉及公司运维规范，但具体信息需查阅相关文档。若未执行检索，无法提供确切答案。建议查阅《运维值班规范》或《应急响应流程》以获取详细信息。
- Engineering reason: 坦承未检索，未提供D-11/15与D-22/45，不虚构具体角色。
- Actual evidence IDs:
- B1 incorrect: 根据内部资料检索结果：

1. **二线值守角色**：
   - 角色为 **D-22**（根据DUTY-7B文件）
   - 响应时间：**45分钟**（二线不承担一线的15分钟响应要求）

2. **一线值守角色**：
   - 未在检索结果中明确提及具体角色
   - 未提供响应时间信息

**补充说明**：
- 一线值守角色和响应时间未在现有资料中明确记载，需进一步查阅完整内部文档或联系相关部门确认。
- 二线信息已明确，但一线信息需结合其他资料或实际操作规范补充。
- Engineering reason: 二线D-22/45分钟正确，但一线D-11/15分钟缺失；未编造一线答案。 上下文复核：实际提供的duty_l2候选明确说二线不承担一线的15分钟要求；回答却说一线响应时间未提供。缺少一线角色是retrieval omission，但关于已提供时间的否定断言不受证据支持。
- Actual evidence IDs: travel_field.txt:ptxt:000, duty_l2.txt:ptxt:000, travel_standard.txt:ptxt:000
- B2 incorrect: 根据现有内部资料检索结果，无法直接获取一线和二线值守角色及响应时间的具体信息。建议查阅更详细的运维手册或联系运维部门获取准确数据。目前可确认的信息如下：

1. **RX-41R2系统**：
   - 值守角色：R-11（每周二10点检查）
   - 响应时间：未明确记录
   - 验收角色：R-22（载荷试验要求18千克，连续运行36小时）

2. **Borealis-2系统**：
   - 负责人角色：B-22（2028年6月20日上线）
   - 响应时间：未明确记录

注：一线/二线的具体值守角色及响应时间可能涉及更详细的运维规范，需通过官方文档或运维团队进一步确认。
- Engineering reason: 没有D-11/15及D-22/45，还把RX-41R2维护R-11标成值守角色，检索错误主题后扩写。
- Actual evidence IDs: robot_r2_service.txt:ptxt:000, borealis2_schedule.txt:ptxt:000, robot_r2_acceptance.txt:ptxt:000

### v2-a-049

- Input: 内部 DUTY-7 升级协调角色的工位编号是多少？
- Expected: 无法确定：未记载工位编号
- B0 correct_abstention: 无法确定内部DUTY-7升级协调角色的工位编号。根据现有信息，需通过搜索内部文档或相关系统配置才能获取准确数据。若需进一步核实，建议查阅项目管理手册或设备分配表。
- Engineering reason: 明确无法确定DUTY-7工位，建议获取文档，不把角色编号当工位。
- Actual evidence IDs:
- B1 incorrect: 根据搜索结果，DUTY-7的升级协调角色对应的工位编号为 **角色 D-33**。但需注意，该信息仅在搜索结果中提及，未明确说明具体工位编号（如物理位置或系统编号）。若需进一步确认工位编号，可能需要参考其他文档或直接联系相关系统管理员。
- Engineering reason: 先将角色D-33当作工位编号；后续没有明确物理编号的限定不能消除错误断言。
- Actual evidence IDs: duty_l1.txt:ptxt:000, duty_escalation.txt:ptxt:000, duty_training.txt:ptxt:000, duty_l2.txt:ptxt:000, borealis2_acceptance.txt:ptxt:000
- B2 incorrect: 根据搜索结果，DUTY-7升级协调角色的工位编号为**角色 D-33**。该信息在《duty_escalation.txt》中明确提及（事件归档号 INC-707），且与其他系统（如DUTY-7B的D-22）区分，属于独立定义的协调角色范畴。
- Engineering reason: 把真实协调角色D-33断言为工位编号，没有工位证据。
- Actual evidence IDs: duty_l1.txt:ptxt:000, duty_escalation.txt:ptxt:000, duty_training.txt:ptxt:000, duty_l2.txt:ptxt:000, borealis2_acceptance.txt:ptxt:000

## Limitations

- 20-query synthetic controlled benchmark; 5 categories x4; single Qwen3:1.7b and single KB tool
- manual corpus/questions and engineering answer judgments; no statistical significance or production-scale claims
- B1固定调度真实tool后单次生成，无planning LLM；B2通常两次LLM且复用较早运行，E2E不是等LLM调用成本/同一时段性能比较
- B1使用原query、同题A2实际top_k；B2可能自主改写query，效果差异不能全部归因routing
- 不新增threshold、Hybrid或Prompt调参；失败不删除、不重复采样挑结果
- judgment input隐藏strategy/category/source-run标签，稳定hash排序，只提供query、gold expected facts/required evidence、candidate。助手已见Phase3A部分B2答案，不能声称真正独立blind；provided-evidence grounding的第二阶段必然不blind。无额外judge模型。

本地Qwen推理主导耗时；检索通常百毫秒级，实际耗时以首轮记录为准。这不是production latency benchmark。每类4题，1题即25个百分点。B2 route 20/20不等于final answer 20/20。

## Reproduction

```powershell
python scripts/v0_2/run_ablation.py --stage init --run-dir artifacts/v0.2/ablation/<first-run>
python scripts/v0_2/run_ablation.py --stage run --strategy B0 --run-dir artifacts/v0.2/ablation/<first-run>
python scripts/v0_2/run_ablation.py --stage run --strategy B1 --run-dir artifacts/v0.2/ablation/<first-run>
python scripts/v0_2/run_ablation.py --stage judge-input --run-dir artifacts/v0.2/ablation/<first-run>
# 按固定rubric保存judgments.json与grounding_review.json，禁止看结果调rubric。
python scripts/v0_2/run_ablation.py --stage report --run-dir artifacts/v0.2/ablation/<first-run>
```
EVAL_CONFIG只写一次；新run-dir可复用该冻结配置但拒绝任何source/rubric/config差异；本次首次目录不可覆盖。独立复现使用全新的artifacts路径，原文件保持不变。B2需要ignored Phase3A原trace、Phase2索引，本快照不能代替raw trace。

## Interpretation — what this comparison establishes

B0 strict 7/20、B1 strict 15/20、B2 strict 14/20。在这20题上，不能用此结果证明Agent Routing最终答案普遍优于Always Retrieve；单题也不能建立因果结论。当前可见收益是按任务省去不必要的知识库调用，而不是消除检索和生成错误。

### A. Direct fastest?

本次B0 E2E mean/median/p95为31.13/26.06/64.44秒，低于B1的50.06/46.56/71.95秒与复用B2的71.93/76.88/121.26秒。B0的15/15私有任务均没有检索，0/4私有单事实、0/4多证据题严格正确，代价是私有事实无证据、拒答或编造。这里的miss是strategy-imposed，不是router error。

### B. Always Retrieve interference and denominator

Frozen labels中expected_tool=null有5条：4个general_no_tool（001/006/021/046）及1个ambiguous_boundary文字处理（010）。所以B1 unnecessary=5/5，其中严格general分类为4/4，而非5个general category。全20题中不必要检索5/20=25%。B0/B2均0/5。
046是实际观察到的无关上下文干扰：用户只问通用一线/二线区别，B1返回二线值守卡、Cedar演示、采购归档，随后以资料无定义拒答；B0和B2正常解释通用区别。该策略失败不算工具执行异常。其他4个不需要KB的B1样本仍正确，不能声称所有无关检索都必然有害。

### C. Agent Routing benefits and costs

B2在原首次A2 test中保持15/15应检索问题、避免5/5无需检索问题，实际工具调用15次而B1为20次，平均0.75而非1.00，减少25%的KB执行。B0漏检索15/15=100%，B1/B2漏检索0/15。B1多检索不是工具错误，B0禁用工具不是路由决策失败。
B2实际35次模型请求，而B1只有20次生成请求；B1固定策略直接执行真实工具，没有规划LLM。工具调用更少不意味着模型请求或E2E更少。本次B2并未胜过B1严格答案分数或耗时。

### D. Routing 20/20 does not establish answer correctness

B2首轮routing正确20/20，但严格最终答案只有14/20；002/005/023/048/049/050仍错。002、005、050必要证据已到达模型仍产生错误附加事实或条件；023、048有检索/证据缺失；049把角色误当工位。未改变Prompt、Tool description、Retriever、query rewrite方式或top_k来修复这些结果。

### E. Layered error attribution

- v2-a-002 — generation, grounding: B1/B2都检到AX-812卡且RX-41主答案正确；B2额外误读不记录Aurora验收要求的范围，严格判错，B1正确。
- v2-a-003 — strategy_imposed_no_retrieval, generation, grounding: B0编造CTO张伟/CFO李敏；B1/B2真实两卡覆盖完整，给A-11/A-33。
- v2-a-004 — strategy_imposed_no_retrieval, grounding: B0匿名按gold判断拒答本身合理；运行上下文证实没有检索，却声称根据内部资料查无面积，按冻结规则改incorrect。B1/B2依据实际候选不足拒答。
- v2-a-005 — generation, grounding: B1/B2均含Aurora和Aurora-X预算卡；B1正确186000，B2把32000单笔采购上限跨项目推到FIN-A12，故strict错误；B0仅定义预算且诚实未获得额度，partial。
- v2-a-023 — retrieval, evidence_completeness, generation, grounding: B1/B2只检到B的模型180天、B的备份30天、A的备份14天，均遗漏A的访问审计60天。生成将14天当所问在线保留期；B1另误称A存模型。B0编造日志和30/60天。
- v2-a-046 — unnecessary_retrieval, generation_task_following: B1强制检索到二线卡/Cedar/采购归档，反而拒绝回答通用一线/二线区别。B0/B2无需私有事实直接正确回答。候选诱发的任务偏离是观察，不是多次重复的因果证明。
- v2-a-048 — retrieval, evidence_completeness, generation, grounding: B1原query保留二线D-22/45，缺一线角色，匿名partial；实际候选已提一线15分钟，答案却说时间未提供，上下文复核incorrect。B2自主改写后两必要卡都没命中，且把R-11维护角色称值守。B0诚实未检索但无答案。
- v2-a-049 — generation, grounding: B0诚实无法确定工位；B1/B2看到D-33升级角色后均当工位编号。B1加未明确具体工位的限定没有消除先前肯定断言。所有返回高相似度也不提供工位事实。
- v2-a-050 — generation, grounding: B1/B2都命中升级20分钟必要卡。B1正确主要条件却加入无证据的自动系统触发和把DUTY-7B说成升级流程；B2把未响应满20分钟改成响应未满20分钟。错误附加私有事实按严格规则判错。B0诚实不知，但有答案问题不能算正确拒答。

## Judgment provenance and context adjudication

60条candidate以stable hash排序，初评只读query、gold、candidate，不读strategy/category。匿名reference初评全部保存后才打开mapping。没有另一个LLM打分；评阅助手此前已见部分Phase3A答案，因此不声称真正独立blind。实际provided-evidence grounding不可盲，单独保存理由。
匿名reference初评与实际上下文复核不是修改rubric：rubric在B0/B1之前已规定未检索却声称资料不存在是unsupported private claim，并规定错误私有断言不能得到correct/partial。两条复核before/after保存在context_adjudications.json，初评blind_judgments.json未覆盖。
- B0 004：匿名根据gold判断面积拒答是correct_abstention；但真实trace没有Tool，回答声称“根据现有内部资料记载，未找到”。依据冻结context规则最终incorrect。其他B0 024/049只是诚实无法确定，仍保留correct_abstention。
- B1 048：匿名为partial（二线正确、一线遗漏）；实际duty_l2已经明确说二线不承担一线15分钟要求，回答却说一线响应时间未提供。最终incorrect；缺少一线角色仍单独标retrieval omission。
初评reference strict为B0 8/20、B1 15/20、B2 14/20；最终应用预注册上下文规则后为7/20、15/20、14/20。所有类别和Strict使用最终judgments.json。Partial不赋分。
Unsupported private claims统计含至少一个不支持/错误私有断言的case数（B0 7、B1 4、B2 6），不是原子claim数量。Grounded与Correct分开：诚实对有答案题表示无法访问可以grounded但incorrect；B1 046通用题拒答不编造私有事实，grounded但incorrect。
Evidence completeness分母在answerable私有题为11：B0 complete/partial/none=0/0/11；B1=9/2/0；B2=9/1/1。其余9题（5个无需私有事实、4个no-answer）not_applicable。Multi-evidence子集固定4题，完整证据B0 0/4、B1 2/4、B2 2/4，完全正确答案也分别0/4、2/4、2/4。

## Execution and freeze audit

Dataset SHA256: `078b30d94d2c4664a30aece15b3c255c9351345edc40a02dca15213b9fae9d18`。
A2 routing config byte SHA256: `4c3df3f3a34215383c76fbde507851a142d81741f8112799bd090ff9495f61d8`。
Rubric/config锁定UTC 2026-10-05 08:40:07；B0首次开始UTC 08:40:11，B1在B0完成后才开始；两组各20题、每题上下文重置、均无resume/重复采样。B2来自原A2各题source_sha256验证，无额外模型或retrieval重跑。
首次20/20 B0请求及20/20 B1请求均HTTP200，无model errors；B1真实20次KB执行均成功，assistant策略调用ID与role=tool正确配对。B2复用35次HTTP200模型请求/15次KB执行，全部source SHA与原trace一致。B1的策略安排tool_call是程序调度，不伪称Qwen生成structured调用。
205项检查全通过：191 pytest（含新增27 ablation tests）+11 plugin verification+3 independent metric checks；pytest耗时13.13秒。全部检查在模型运行结束后执行。模型protocol复核60个case另存原始结果，不混加到205测试口径。
冻结完整性通过：V0.1 25 hashes、V0.2 dataset 45 hashes、186个既有受保护文件、Phase2 33个raw文件、Phase3 routing 154个raw文件、Phase2/3 evidence、A2 config、旧indexes均未变化。nanobot clean；README/简历未变。旧tag仍指向aa422d826fa484933d9949c16fc79e1a2f22eda1。HEAD仍93293f54be1d62446123eba977c5ece2703a4552，未commit或push。

## Timing definitions and runtime limitations

B0 Tool/LLM1为not_applicable；其唯一请求就是最终生成。B1 Tool统计20次，均值208.28ms、中位155.07ms、p95 297.64ms；无规划LLM1，唯一模型请求为最终生成（不是伪造第二次请求）。B2工具统计15次，均值222.79ms、中位208.82ms、p95 299.73ms；规划LLM1统计15次，最终生成LLM统计全部20次。上面的latency节给出各组原始聚合，不能把n=15和n=20分项直接相加成平均E2E。
Qwen本地推理为主要耗时，retrieval约百毫秒级。B0/B1本次顺序执行，B2复用较早运行，无时段/缓存/输出长度控制，不是同等模型调用成本的性能实验。p95用线性分位数，样本只有20，不是可靠尾延迟估计。
nanobot逻辑context_window_tokens=200000是原冻结配置；实际Ollama /api/ps显示4096。未修改任一值，未因此重跑。现有HTTP调用没有显式新num_ctx；这不能解释为实际200k上下文。
只读/api/ps观察size_vram=0（CPU）、qwen3上下文4096；不调整资源或模型参数。本轮单次采样temperature=.1，不能量化模型随机性、跨运行方差或统计显著性。

## Files and reproducibility boundaries

新增实验实现：experiments/v0_2/ablation/{config,runner,evaluate,reporting}.py、__init__.py、EVAL_CONFIG.json；CLI scripts/v0_2/run_ablation.py；测试tests/v0_2/test_ablation.py。只有这些新文件与两个新报告待审阅，既有tracked内容不变。
本轮原始B0/B1/B2 JSON、完整requests/工具参数/evidence、匿名评分、上下文复核、protocol与validation保存在ignored artifacts/v0.2/ablation/phase3b_first_20261005/，raw_manifest.json封存所有JSON SHA256。可提交的小型PHASE3_ABLATION.json保留配置、评分理由、指标、类别、bad-case IDs和原始manifest；不上传大型raw traces。
重新运行必须选新run目录，拒绝覆盖首次目录；B2复用需要Phase3A本地原始trace与Phase2 frozen index，GitHub小型证据快照不能还原全部token流。没有这些本地ignored依赖时应停止说明，不能自行重跑A2冒充首次结果。
首次聚合report命令对当前两个输出报告使用排他创建；它也不会覆写已经存在的报告。独立复现若要保留另一轮Markdown/JSON报告，需要明确新的报告路径/版本方案后再实施，当前不为此改变冻结代码。现有CLI的可重复部分为新run目录与原始JSON，当前首次报告聚合不可重复覆盖。
未来可评估更强模型、检索覆盖、证据约束等，但本阶段不实现、不依据当前test调优。

## Phase 3C — independent audit and freeze checkpoint

独立标准库计算直接读取首次raw cases、final judgments与grounding_review，未调用已有summarize/evaluator；所有分类计数、Strict、类别指标、工具使用、证据覆盖、拒答、Grounded、unsupported cases及mean/median/p95与快照一致。没有重跑模型，没有修改judgment；75个原始JSON与首次raw manifest全部一致。
随机抽样seed=20261005，逐组抽查且不重复：009（B0错/B1+B2对）、046（B1错/B2对）、005（B2错/B1对）、023（三者错）、002（routing对/answer错）。Gold、实际候选、原始回答与评分理由复核均成立。两阶段评分的原始来源、hash及无法完全blind的限制已显式放入PHASE3_ABLATION.json的judgment_provenance。

### Concise B2 error taxonomy

以下标签不互斥，不能相加作为独立错误数量：
- routing：0/6；无。B2对20题的是否检索判断均正确，六个最终答案错误都在后续层。
- query_rewrite：1/6；v2-a-048。同题B1原query返回duty_l2，B2改写为一线 二线 角色 值守 响应时间后零required chunk；配对观察为partial→none，不声称多次采样的因果结论。
- retrieval_ranking：2/6；v2-a-023, v2-a-048。023审计主卡未入Top3；048两张值守主卡都未入Top3。
- evidence_completeness：2/6；v2-a-023, v2-a-048。分别partial（1/2 required）与none（0/2 required）。
- entity_or_fact_type_confusion：5/6；v2-a-002, v2-a-005, v2-a-023, v2-a-048, v2-a-049。002限定范围、005项目政策、023审计与备份、048维护与值守、049角色与工位混淆。
- generation_or_grounding：6/6；v2-a-002, v2-a-005, v2-a-023, v2-a-048, v2-a-049, v2-a-050。错误私有附加断言、误用候选证据或条件改写；050必要证据已送达但未响应满20分钟条件被反转。

### Formal conclusion

在本次20-query synthetic benchmark中，Direct对private查询不足；Always Retrieve取得最高Strict 15/20，Agent Routing为14/20。Agent Routing消除了5/5不必要检索（4个general分类+1个boundary文字处理），没有missed retrieval，但未全面优于Always Retrieve最终答案质量。
Agent Routing减少了不必要retrieval，但在当前runtime/local model条件下没有降低E2E latency：B0 mean 31.13s、B1 50.06s、B2 71.93s。B1固定策略没有planning LLM；B2通常LLM1+Tool+LLM2，其planning均值33.80s远高于Tool约0.223s。本地Qwen推理占主要延迟。B2复用較早运行，时段、调用数、上下文和输出长度不同；不能推导Agent Routing普遍更慢或Always Retrieve普遍更快。

### Validation and publication scope

本次重新运行191 pytest（10.73秒）+11 plugin verification+3 independent metric checks=205，全通过。既有fitz弃用警告仍保留，没有通过改依赖绕过。
V0.1 25 hashes、V0.2 45 hashes、Phase2/Phase3 routing evidence、A2 config、既有index/metadata与nanobot均验证不变。Phase3B的未commit状态文字是当时快照；本Phase3C批准只提交10个Ablation实现/测试/config/报告文件。原始artifacts和本轮审计产物仍ignored，不纳入commit。README、简历、main及旧tag不改。
完整raw依赖及首次报告排他创建限制继续保留；本阶段不通过改实验代码绕过这些边界。
