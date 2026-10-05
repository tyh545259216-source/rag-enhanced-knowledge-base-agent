# V0.2 Routing Bad Cases

所有 FN/FP 均保留；分类来自本轮助手逐条工程审阅，未独立人工复核，是原因候选而非因果证明。

## dev/A0/v2-a-017 — FN

- Category: private_single_fact
- Input: 内部 RX-41R3 的载荷验收目标是多少千克？
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定RX-41R3的具体载荷验收目标。建议查阅相关技术文档或制造商规格书以获取准确数据。
- Suspected causes: private_fact_not_recognized, system_instruction_weak
- Engineering analysis: 明确问内部验收目标，却未查库而建议查制造商规格；观察支持私有依赖未识别，无法证明模型内部原因。

## dev/A0/v2-a-019 — FN

- Category: private_no_answer
- Input: 内部 RX-41R2 机器人整机价格有多少？
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定RX-41R2机器人的具体整机价格，因为该型号可能属于特定品牌或系列，且相关信息可能未公开或未收录在内部知识库中。建议查阅官方渠道或联系销售部门获取准确报价。
- Suspected causes: private_fact_not_recognized, system_instruction_weak
- Engineering analysis: 未检索便假设型号信息可能未公开/未收录，转向销售渠道；属于 FN，不把不确定表达当作检索。

## dev/A0/v2-a-033 — FN

- Category: private_multi_evidence
- Input: 按内部表对比 Cedar 的演示冻结日与正式发布日期。
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定具体的内部表名称或结构，因此无法直接对比演示冻结日与正式发布日期。建议提供更详细的表名或字段信息，或检查相关数据库结构以获取对比依据。
- Suspected causes: ambiguous_query, tool_description_too_narrow
- Engineering analysis: 把内部表理解为需用户提供数据库结构；自然语言检索能力未被使用，表述歧义/描述范围只是原因候选。

## dev/A0/v2-a-040 — FN

- Category: ambiguous_boundary
- Input: 一般采购会有金额上限；我们内部设备资本采购实际封顶多少？
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定内部设备资本采购的具体封顶金额。建议查阅公司内部采购政策文件或与相关部门沟通获取准确信息。
- Suspected causes: system_instruction_weak, private_fact_not_recognized
- Engineering analysis: 混合常识与本单位政策的问题直接拒答，未处理私有具体上限；通用指令较弱是候选解释。

## dev/A0/v2-a-042 — FN

- Category: private_single_fact
- Input: 内部 LOG-31T 的管理角色是谁？
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定内部LOG-31T的具体管理角色。建议查阅相关系统文档或联系负责该系统的管理员以获取准确信息。
- Suspected causes: private_fact_not_recognized, system_instruction_weak
- Engineering analysis: 内部管理角色问题直接建议联系管理员，未使用已提供工具；私有事实依赖未识别是观察层解释。

## dev/A1/v2-a-013 — FN

- Category: private_multi_evidence
- Input: 内部普通差旅与现场差旅的住宿上限各是多少？
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定具体的住宿上限数值，但通常企业差旅住宿费标准会根据差旅等级（如普通/高级）和地点（如一线城市/二三线城市）有所不同。建议查阅公司内部的差旅管理办法或联系相关部门获取准确信息。
- Suspected causes: private_fact_not_recognized, system_instruction_weak
- Engineering analysis: 未调用工具就要求用户自行查资料或直接表示未知；只有描述变化不能稳定触发私有检索。单次实验含采样随机性，不能证明描述造成失败。

## dev/A1/v2-a-014 — FN

- Category: private_no_answer
- Input: 按内部政策，TR-11 是否覆盖教材运费？
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 根据内部政策文件，TR-11政策明确覆盖教材运费，但仅限于教材采购合同中明确包含运费条款的特殊情况。具体实施范围和条件需参照相关合同条款执行。
- Suspected causes: private_fact_not_recognized, system_instruction_weak
- Engineering analysis: 未检索却断言内部政策覆盖教材运费并附加合同条件；golden 标注该事实不存在。既是 routing FN，也是观察到的无证据生成断言；不能只归为 Retrieval 错误。

## dev/A1/v2-a-028 — FN

- Category: private_multi_evidence
- Input: 根据内部两份预约表比较 ORBIT-3 与 ORBIT-3A 的开放时段。
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定ORBIT-3与ORBIT-3A的开放时段比较结果，因为缺乏具体的内部预约表数据。建议查阅相关预约表或联系负责人员获取详细信息。
- Suspected causes: ambiguous_query, model_capability
- Engineering analysis: 以缺少表名/表数据为由停止，未先检索；描述已说明不需精确表名，歧义理解及小模型能力是候选原因。

## dev/A1/v2-a-030 — FN

- Category: ambiguous_boundary
- Input: 我问的是内部 RM-003 的容量，不是一般会议室的人数估算；最多能坐几人？
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定内部RM-003的具体容量。建议检查相关会议室的详细规格或联系管理团队获取准确数据。若需估算一般会议室人数，通常可参考标准容量（如20-30人），但此信息未明确提供。
- Suspected causes: private_fact_not_recognized, system_instruction_weak
- Engineering analysis: 未查内部容量，却附带一般会议室20–30人的估算，违背用户已明确排除的估算语境；routing 与 generation/policy 均有问题。

## dev/A1/v2-a-032 — FN

- Category: private_single_fact
- Input: 内部 Cedar 正式发布表指定的发布角色是谁？
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定内部Cedar正式发布表指定的发布角色。建议查阅Cedar项目官方文档或联系项目维护团队获取准确信息。
- Suspected causes: private_fact_not_recognized, system_instruction_weak
- Engineering analysis: 未调用工具就要求用户自行查资料或直接表示未知；只有描述变化不能稳定触发私有检索。单次实验含采样随机性，不能证明描述造成失败。

## dev/A1/v2-a-033 — FN

- Category: private_multi_evidence
- Input: 按内部表对比 Cedar 的演示冻结日与正式发布日期。
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定具体内部表的名称或数据内容，需要更多信息（如表名或相关描述）才能进行对比。建议检查相关系统表或数据库结构以获取准确信息。
- Suspected causes: ambiguous_query, model_capability
- Engineering analysis: 以缺少表名/表数据为由停止，未先检索；描述已说明不需精确表名，歧义理解及小模型能力是候选原因。

## dev/A1/v2-a-039 — FN

- Category: private_no_answer
- Input: 内部 CAB-21C 归档柜的实体楼层是哪层？
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定CAB-21C归档柜的实体楼层信息。建议查阅相关建筑布局图或联系图书馆管理部门获取准确信息。
- Suspected causes: private_fact_not_recognized, system_instruction_weak
- Engineering analysis: 未调用工具就要求用户自行查资料或直接表示未知；只有描述变化不能稳定触发私有检索。单次实验含采样随机性，不能证明描述造成失败。

## dev/A2/v2-a-020 — FP

- Category: ambiguous_boundary
- Input: 机器人通常要保养，请给出通用的保养记录表字段，别查本单位设备。
- Expected route: None
- Actual calls: [{"id": "call_gh8x6il8", "name": "search_knowledge_base", "arguments": {"query": "机器人保养记录表通用字段", "top_k": 3}, "request_index": 1, "native_structured": true}]
- First response: None
- Suspected causes: general_question_misclassified, tool_description_too_broad, model_capability
- Engineering analysis: 用户明确要通用表字段且禁止查本单位设备，仍真实调用 KB。观察确认 FP/约束违背；工具可用性过强或否定约束识别不足只是候选原因，不能证明具体因果。最终答复可给通用字段并不抵消 FP。

## test/A0/v2-a-003 — FN

- Category: private_multi_evidence
- Input: 按内部记录分别给出 Aurora 的项目负责人和财务审批负责人。
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定Aurora项目的具体负责人和财务审批负责人，因为相关内部记录可能未被公开或未在知识库中检索到。建议通过官方渠道或联系相关负责人获取准确信息。
- Suspected causes: private_fact_not_recognized, system_instruction_weak
- Engineering analysis: 未检索就说内部记录可能未在知识库中检索到；私有两职责任务被直接拒答。A2 调用后两份必要资料齐全、正确区分 A-11/A-33。

## test/A0/v2-a-005 — FN

- Category: ambiguous_boundary
- Input: 预算这个词是什么意思？请以内部 FIN-A12 批准单的具体额度举例。
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定内部FIN-A12批准单的具体额度，但“预算”通常指计划未来收入和支出的财务安排。例如，FIN-A12可能涉及年度预算，额度可能在100万至200万之间（具体需参考批准单文件）。建议查阅相关文件获取准确数据。
- Suspected causes: ambiguous_query, system_instruction_weak
- Engineering analysis: 只解释通用预算并猜测100万至200万，未查询明确指定的FIN-A12。A2修复路由但仍将FIN-AX12采购上限混入，属生成解释失败。

## test/A0/v2-a-007 — FN

- Category: private_single_fact
- Input: B2-620 的上线工作交给了哪个角色？
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定B2-620的上线工作具体由哪个角色负责，因为缺乏关于该编号的上下文信息（如项目名称、产品类型或组织架构）。建议提供更多背景信息以便准确回答。
- Suspected causes: private_fact_not_recognized, tool_description_too_narrow
- Engineering analysis: 把B2-620缺少上下文当作要求用户补背景的理由，跳过可用自然语言知识库查询；A2找到B-22。

## test/A0/v2-a-008 — FN

- Category: private_multi_evidence
- Input: 请按内部排期区分 BO-620 演示日期和 B2-620 上线日期。
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定BO-620的演示日期和B2-620的上线日期，因为相关排期信息未在内部知识库中提供。建议查阅公司内部项目管理系统的最新公告或联系产品团队获取准确信息。
- Suspected causes: private_fact_not_recognized, system_instruction_weak
- Engineering analysis: 未检索却声称排期未在内部知识库提供；A2检索后BO-620与B2-620的两日期均得到支持。

## test/A0/v2-a-023 — FN

- Category: private_multi_evidence
- Input: 按内部卡片比较 SABLE-18 与 SABLE-18B 各自保存什么、保留多久。
- Expected route: search_knowledge_base
- Actual calls: []
- First response: 无法确定SABLE-18和SABLE-18B的具体存储介质类型及数据保留时间。建议查阅官方技术文档或联系技术支持获取准确信息。
- Suspected causes: ambiguous_query, private_fact_not_recognized
- Engineering analysis: 将保存什么解释为存储介质并转向官方文档，未执行内部卡片搜索。A2修复路由，但Top3漏在线审计卡且把备份14天当在线审计保留时间。

## 不混淆失败层

路由正确与Retrieval coverage、证据解释、拒答是不同层。A0漏路由5题由A2修复；test无回退和双方路由皆错，但dev A2误调用保留。A2 test仍有v2-a-005跨实体推测、023漏审计证据/14天误用、048无正确证据、049将D-33角色当工位编号的幻觉。A0/A2都出现049答案错误，不能因为两者路由TP就略去。只保留观测与工程原因候选，不根据test重新调参。

## 正式 test 配对审计

A0错/A2对：v2-a-003, v2-a-005, v2-a-007, v2-a-008, v2-a-023；分别为两职责查询、通用预算+内部额度边界、上线角色、两项目排期比较、两服务器存储/保留比较。
A0对/A2错：无。双方路由都错：无。仅报告实际观察，不造样本。前三个multi-evidence漏调用被修复，但v2-a-023最终答案仍不完整/错误。

## 路由正确后仍可能失败

下列案例是首次trace的答案/证据层观察，不添加到routing FN/FP。每项Expected来自冻结golden/corpus，Actual直接引用首轮final_response。没有再次推理或模型judge。

### A2/v2-a-002

- Input: 内部验收卡上 AX-812 用的是哪台设备？
- Expected: RX-41
- Actual: 根据内部验收卡记录，项目编号为AX-812的设备为**RX-41**。该设备属于Aurora-X项目，验收负责人角色为A-22，且验收要求不记录在该卡中。需注意，AX-812与AU-812为不同项目，前者涉及Aurora-X，后者为2028年年度值守项目。
- Failed layer: generation/evidence interpretation
- Analysis: 主答案 RX-41 正确，但追加“验收要求不记录在该卡中”与该卡明确96小时矛盾；原卡说不记录Aurora（非Aurora-X）的验收要求。
- Actual tool evidence: [[{"rank": 1, "text": "Aurora-X 项目编号 AX-812，验收负责人为角色 A-22。验收设备是 RX-41，要求连续运行 96 小时。此卡不记录 Aurora 的验收要求。", "source": "aurora_x_acceptance.txt", "chunk_id": "aurora_x_acceptance.txt:ptxt:000", "score": 0.7434781789779663, "page": null}, {"rank": 2, "text": "Aurora 的 2028 年度值守项目编号为 AU-812，项目负责人是角色 A-11。轮值从 2028 年 3 月 6 日开始，和旧版本发布名册分开管理。", "source": "aurora_roster.txt", "chunk_id": "aurora_roster.txt:ptxt:000", "score": 0.6816309690475464, "page": null}, {"rank": 3, "text": "机器人 RX-41R2 的维护角色为角色 R-11，每周二 10 点检查。型号后缀 R2 不可省略，维修登记号为 MA-412。", "source": "robot_r2_service.txt", "chunk_id": "robot_r2_service.txt:ptxt:000", "score": 0.6574497818946838, "page": null}]]

### A2/v2-a-005

- Input: 预算这个词是什么意思？请以内部 FIN-A12 批准单的具体额度举例。
- Expected: 可说明预算含义；内部额度为 186000 元
- Actual: 预算是指为实现特定目标而预先规划的财务资源分配方案。以内部政策FIN-A12为例，Aurora的2028年预算金额为**186,000元**，审批负责人为角色A-33，该预算用于项目管理相关支出。该政策的单笔采购上限为32,000元（根据Aurora-X的预算数据推测，具体数值可能因政策版本差异而略有不同）。
- Failed layer: generation/entity evidence interpretation
- Analysis: 186000预算正确，但将 Aurora-X / FIN-AX12 的32000采购上限推给 FIN-A12；query意图完整、证据存在，属于跨实体推测。
- Actual tool evidence: [[{"rank": 1, "text": "Aurora 的 2028 年预算为 186000 元，财务审批负责人是角色 A-33，政策编号 FIN-A12。审批角色不担任项目负责人。", "source": "aurora_finance.txt", "chunk_id": "aurora_finance.txt:ptxt:000", "score": 0.726618766784668, "page": null}, {"rank": 2, "text": "Aurora-X 的预算为 216000 元，审批负责人是角色 A-44，政策编号 FIN-AX12。单笔采购上限为 32000 元。", "source": "aurora_x_finance.txt", "chunk_id": "aurora_x_finance.txt:ptxt:000", "score": 0.651349663734436, "page": null}]]

### A2/v2-a-023

- Input: 按内部卡片比较 SABLE-18 与 SABLE-18B 各自保存什么、保留多久。
- Expected: 访问审计60天；模型权重180天
- Actual: 根据内部文档信息：

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
- Failed layer: retrieval coverage + generation
- Analysis: Top3只有SABLE-18B模型、SABLE-18B备份、SABLE-18备份，漏sable18_audit；在线审计应60天，回答误为14天。
- Actual tool evidence: [[{"rank": 1, "text": "服务器 SABLE-18B 保存模型权重，模型归档保留 180 天，角色为角色 S-33。系统编号 SV-18B，与访问审计无关。", "source": "sable18b_model.txt", "chunk_id": "sable18b_model.txt:ptxt:000", "score": 0.9284074306488037, "page": null}, {"rank": 2, "text": "SABLE-18B 的模型备份于每天 04:00 执行，备份保留 30 天，角色为角色 S-44。不能用 SABLE-18 的备份窗口替代。", "source": "sable18b_backup.txt", "chunk_id": "sable18b_backup.txt:ptxt:000", "score": 0.9033946990966797, "page": null}, {"rank": 3, "text": "SABLE-18 的审计备份于每天 02:30 开始，备份角色为角色 S-22。备份保留 14 天，不是在线审计记录的保留时间。", "source": "sable18_backup.txt", "chunk_id": "sable18_backup.txt:ptxt:000", "score": 0.8801753520965576, "page": null}]]

### A2/v2-a-048

- Input: 按照内部资料，一线和二线各由哪个角色值守、分别多久响应？
- Expected: D-11 15分钟；D-22 45分钟
- Actual: 根据现有内部资料检索结果，无法直接获取一线和二线值守角色及响应时间的具体信息。建议查阅更详细的运维手册或联系运维部门获取准确数据。目前可确认的信息如下：

1. **RX-41R2系统**：
   - 值守角色：R-11（每周二10点检查）
   - 响应时间：未明确记录
   - 验收角色：R-22（载荷试验要求18千克，连续运行36小时）

2. **Borealis-2系统**：
   - 负责人角色：B-22（2028年6月20日上线）
   - 响应时间：未明确记录

注：一线/二线的具体值守角色及响应时间可能涉及更详细的运维规范，需通过官方文档或运维团队进一步确认。
- Failed layer: retrieval coverage + generation
- Analysis: Top3无一线/二线必要chunk；模型未给出期望D-11/15分钟与D-22/45分钟，并把无关机器人维护角色作为补充。A0同题Top3含二线卡，A2零必要证据；意图保留不保证证据保留。
- Actual tool evidence: [[{"rank": 1, "text": "机器人 RX-41R2 的维护角色为角色 R-11，每周二 10 点检查。型号后缀 R2 不可省略，维修登记号为 MA-412。", "source": "robot_r2_service.txt", "chunk_id": "robot_r2_service.txt:ptxt:000", "score": 0.6552635431289673, "page": null}, {"rank": 2, "text": "Borealis-2 编号 B2-620，正式上线定于 2028 年 6 月 20 日。上线负责人是角色 B-22，不沿用 Borealis 的演示日期。", "source": "borealis2_schedule.txt", "chunk_id": "borealis2_schedule.txt:ptxt:000", "score": 0.6430761814117432, "page": null}, {"rank": 3, "text": "RX-41R2 的验收角色为角色 R-22，载荷试验要求 18 千克，连续运行 36 小时。维护签字不代替验收签字。", "source": "robot_r2_acceptance.txt", "chunk_id": "robot_r2_acceptance.txt:ptxt:000", "score": 0.6342517733573914, "page": null}]]

### A0 and A2/v2-a-049

- Input: 内部 DUTY-7 升级协调角色的工位编号是多少？
- Expected: 无法确定：未记载工位编号
- Actual: 根据搜索结果，DUTY-7升级协调角色的工位编号为**角色 D-33**。该信息在《duty_escalation.txt》中明确提及（事件归档号 INC-707），且与其他系统（如DUTY-7B的D-22）区分，属于独立定义的协调角色范畴。
- Failed layer: generation/no-answer hallucination
- Analysis: 两者均错误把角色D-33说成工位编号；工具返回无工位事实。A0还把一线15分钟附给升级协调角色。
- Actual tool evidence: [[{"rank": 1, "text": "DUTY-7 的一线值班角色为角色 D-11，响应期限 15 分钟。排班起始日 2028 年 10 月 1 日，二线响应另见 DUTY-7B。", "source": "duty_l1.txt", "chunk_id": "duty_l1.txt:ptxt:000", "score": 0.8975069522857666, "page": null}, {"rank": 2, "text": "DUTY-7 在一线未响应满 20 分钟时升级，升级协调角色是角色 D-33，事件归档号 INC-707。升级不等于二线响应期限。", "source": "duty_escalation.txt", "chunk_id": "duty_escalation.txt:ptxt:000", "score": 0.889525830745697, "page": null}, {"rank": 3, "text": "DUTY-8 为桌面演练，角色为角色 D-44，每月 8 日执行。演练响应目标 5 分钟，不用于真实 DUTY-7 事件。", "source": "duty_training.txt", "chunk_id": "duty_training.txt:ptxt:000", "score": 0.8651295304298401, "page": null}, {"rank": 4, "text": "DUTY-7B 的二线响应期限 45 分钟，二线角色为角色 D-22。二线不承担一线的 15 分钟响应要求。", "source": "duty_l2.txt", "chunk_id": "duty_l2.txt:ptxt:000", "score": 0.8469706177711487, "page": null}, {"rank": 5, "text": "Borealis-2 的验收设备 BT-7B 必须连跑 84 小时，由角色 B-44 签字。BT-7 的旧报告不能替代本次验收。", "source": "borealis2_acceptance.txt", "chunk_id": "borealis2_acceptance.txt:ptxt:000", "score": 0.6746656894683838, "page": null}]]

### A2/v2-a-050

- Input: 一线响应一般越快越好；但内部 DUTY-7 超时升级究竟在几分钟触发？
- Expected: 未响应满 20 分钟
- Actual: 根据搜索结果，DUTY-7超时升级的触发时间与一线响应的持续时间相关。具体而言：

1. **升级触发条件**：当一线响应未满20分钟时，系统会触发升级（对应角色D-33，事件归档号INC-707）。
2. **时间范围**：该升级机制的触发时间明确为**20分钟**，即当一线响应未完成20分钟时启动协调角色。

因此，DUTY-7超时升级的触发时间**具体为20分钟**，但需注意该机制仅适用于真实事件，且与一线响应的持续时间直接关联。
- Failed layer: generation/condition interpretation
- Analysis: 20分钟数值正确，但部分句子变成“一线响应未满20分钟”，未清楚表达未响应持续满20分钟，存在触发条件措辞错误。
- Actual tool evidence: [[{"rank": 1, "text": "DUTY-7 的一线值班角色为角色 D-11，响应期限 15 分钟。排班起始日 2028 年 10 月 1 日，二线响应另见 DUTY-7B。", "source": "duty_l1.txt", "chunk_id": "duty_l1.txt:ptxt:000", "score": 0.8751077651977539, "page": null}, {"rank": 2, "text": "DUTY-7 在一线未响应满 20 分钟时升级，升级协调角色是角色 D-33，事件归档号 INC-707。升级不等于二线响应期限。", "source": "duty_escalation.txt", "chunk_id": "duty_escalation.txt:ptxt:000", "score": 0.8644132018089294, "page": null}, {"rank": 3, "text": "DUTY-8 为桌面演练，角色为角色 D-44，每月 8 日执行。演练响应目标 5 分钟，不用于真实 DUTY-7 事件。", "source": "duty_training.txt", "chunk_id": "duty_training.txt:ptxt:000", "score": 0.8353331089019775, "page": null}]]

### A0/v2-a-001

- Input: 我把 Python 变量命名为 Aurora；请解释字符串不可变的含义，不查询内部项目资料。
- Expected: 字符串对象创建后内容不能原地修改
- Actual: Python的变量命名规则中，变量名不能是Python的保留字（如`def`、`class`等），但允许用户自定义任意名称，包括包含特殊字符的名称（如`Aurora`）。这与字符串不可变的特性无关，而是变量命名的语法规则。

字符串在Python中是**不可变**的，意味着一旦创建，其内容无法直接修改。例如：
```python
s = "Aurora"
s = "New Aurora"  # 这行代码会报错，因为字符串不可变
```
因此，虽然变量名可以命名为`Aurora`，但字符串的不可变性意味着无法直接修改其内容，必须通过创建新字符串对象来实现修改。
- Failed layer: general answer generation
- Analysis: 无工具路由正确，但声称对变量重新赋字符串会报错，这是普通Python知识回答错误。
- Actual tool evidence: []

## No-answer 与高相似度

A2 private_no_answer 路由4/4，但v2-a-049把D-33角色当工位编号；Top1 score约0.8975、Top2约0.8895依然不含工位答案。High similarity does not imply answer existence. 不添加threshold；不把误答归咎工具传输。
A0同题也作了同样角色/工位误判，另将15分钟一线响应附给升级协调角色。这是双方答案都错的实际案例，与“双方路由都错=0”不矛盾。

## 处理边界

以上仅保存失败观察。未改Retriever/Prompt/描述/测试集/模型、未再次选择配置、未重跑test。工程原因候选不代表证明模型内部机制；后续若要改进必须新阶段、dev验证和新的独立实验产物。
