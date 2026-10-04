# Demo — real V1 smoke

每个Case独立会话，只开放search_knowledge_base，固定Phase3B通用instruction，无题目特定提示。以下是新真实输出，不是理想答案或模拟结果。一般WebUI完整上下文可能不同。

## Demo 1
Input: 你好！
Actual tool: none
LLM requests: 1，HTTP200，E2E 16.24秒。
Actual final answer:
您好！有什么可以帮助您的吗？

## Demo 2
Input: 项目 Aurora 的负责人是谁？
Actual tool: ['search_knowledge_base']
LLM requests: 2，HTTP200，E2E 109.48秒。
Model tool_calls: search_knowledge_base({"top_k": 5, "query": "项目Aurora 负责人"})
role sequence: system → user → assistant(tool_calls) → tool → assistant(final)
Top-K evidence:
- 1. note_02.txt / note_02.txt:ptxt:000 / score=0.863841: 项目 Aurora 的验收负责人是周岚。验收要求机器人 RB-204 连续运行 72 小时，并提交日志报告。
- 2. note_01.txt / note_01.txt:ptxt:000 / score=0.831053: 项目 Aurora 的负责人是林澈，内部代号 AU-731。首次内部发布日期为 2026 年 11 月 18 日。这是虚构内部资料。
- 3. note_03.txt / note_03.txt:ptxt:000 / score=0.800817: 项目 Aurora 的预算为 128000 元。审批人是顾宁，预算编号 FIN-602；采购上限为 24000 元。
- 4. note_05.txt / note_05.txt:ptxt:000 / score=0.788276: 机器人 RB-204 的维护负责人是孟溪，每周三 16 点检查；它属于 Aurora 验收设备。
- 5. note_06.txt / note_06.txt:ptxt:000 / score=0.755064: 内部服务器 SABLE-17 存放 Aurora 的验收日志，负责人是周岚，日志保留 45 天。
Actual final answer:
根据搜索结果，项目Aurora的负责人存在不同表述：

1. **林澈**（内部代号AU-731）：首次内部发布日期为2026年11月18日，明确指出其为项目负责人。
2. **周岚**：作为验收负责人，负责机器人RB-204的连续运行及日志提交，但未明确说明其是否为项目整体负责人。

由于不同资料的表述存在差异（如林澈与周岚的职责分工），需结合具体上下文判断。若问题指向项目整体负责人，最直接的表述为**林澈**；若关注验收相关职责，则为**周岚**。但根据常规项目管理逻辑，**林澈**更可能为项目整体负责人。

## Demo 3
Input: ORBIT-3 会议室最多容纳多少人？
Actual tool: ['search_knowledge_base']
LLM requests: 2，HTTP200，E2E 65.73秒。
Model tool_calls: search_knowledge_base({"query": "ORBIT-3 容量", "top_k": 5})
role sequence: system → user → assistant(tool_calls) → tool → assistant(final)
Top-K evidence:
- 1. note_09.txt / note_09.txt:ptxt:000 / score=0.828958: 会议室 ORBIT-3 的预约管理员是唐越，开放时间为工作日 9 点至 18 点。
- 2. note_03.txt / note_03.txt:ptxt:000 / score=0.536170: 项目 Aurora 的预算为 128000 元。审批人是顾宁，预算编号 FIN-602；采购上限为 24000 元。
- 3. note_06.txt / note_06.txt:ptxt:000 / score=0.519095: 内部服务器 SABLE-17 存放 Aurora 的验收日志，负责人是周岚，日志保留 45 天。
- 4. note_04.txt / note_04.txt:ptxt:000 / score=0.505578: 项目 Borealis 的负责人是许舟，内部代号 BO-415，发布日期为 2027 年 2 月 9 日。
- 5. note_01.txt / note_01.txt:ptxt:000 / score=0.502943: 项目 Aurora 的负责人是林澈，内部代号 AU-731。首次内部发布日期为 2026 年 11 月 18 日。这是虚构内部资料。
Actual final answer:
无法确定ORBIT-3会议室的容纳人数。提供的知识库信息中未提及该会议室的容量数据，相关资料仅涉及其他项目（如Aurora、Borealis等）的管理信息或日志记录，未包含关于ORBIT-3容量的描述。

## Honest interpretation
Demo2回答林澈但带不必要的职责犹豫；Demo3拒答正确，但“资料仅其他项目”的概括错误。这些是已知生成质量问题，未调prompt或过滤输出。第四题强制调用烟雾成功，仅用于structured transport，不作为自主路由演示。
完整messages/schema/deltas/tool result见 releases/SMOKE_TRACE.json。