# Phase 3A forced structured tool calling

新 nanobot Python 进程，真实 ToolLoader entry point → ToolRegistry → AgentRunner → execute_tool_calls → 外部插件。未启动 Gateway/WebUI，不代表其当前进程刷新过插件。
Provider=ollama，model=qwen3:1.7b，HTTP endpoint=htt<LOCAL_PATH>
仅开放 search_knowledge_base。Python不构造模型调用；原始delta.tool_calls在trace中记录。
完整消息、schema、raw/parsed调用、ToolResult和回答见trace.json；messages可能含模型自行返回的reasoning_content。

## 三个初始实验
### Case 1
项目 Aurora 的负责人是谁？
Tool call: [{'id': 'call_okp7f2vp', 'name': 'search_knowledge_base', 'arguments': {'query': '项目 Aurora 的负责人是谁？', 'top_k': 3}}]
Roles: ['system', 'user', 'assistant', 'tool']，对应call id检查=True
Integration success=True；baseline exact match=True
最终回答：根据搜索结果，项目Aurora的负责人是林澈（内部代号AU-731）。该信息来源于资料note_01.txt，明确指出其为项目负责人。
### Case 2
Aurora 项目如何验收、使用哪台机器人、验收日志存在哪里？
Tool call: [{'id': 'call_d9yxgw94', 'name': 'search_knowledge_base', 'arguments': {'query': 'Aurora 项目如何验收、使用哪台机器人、验收日志存在哪里？', 'top_k': 3}}]
Roles: ['system', 'user', 'assistant', 'tool']，对应call id检查=True
Integration success=True；baseline exact match=True
最终回答：根据现有资料：  
1. **验收负责人**为周岚，验收要求机器人RB-204连续运行72小时并提交日志报告。  
2. **验收日志**存储在内部服务器SABLE-17，保留45天。  
3. 项目负责人信息（林澈）及内部代号（AU-731）为虚构内容，不作为有效信息。  

综上，Aurora项目验收使用RB-204机器人，日志存于SABLE-17服务器。
### Case 3
ORBIT-3 会议室最多容纳多少人？
Tool call: [{'id': 'call_jauxl5es', 'name': 'search_knowledge_base', 'arguments': {'top_k': 3, 'query': 'ORBIT-3 会议室 最多容纳多少人'}}]
Roles: ['system', 'user', 'assistant', 'tool']，对应call id检查=True
Integration success=True；baseline exact match=False
最终回答：根据当前资料无法确定ORBIT-3会议室的容纳人数。

## 分层判定
Case 1：选择、参数、检索、传输、证据忠实性、答案正确性均通过。
Case 2：前四层通过；所问验收事实正确，但额外以“虚构”为由否定负责人资料，属于无依据的证据有效性判断，不能标为完全 grounded。
Case 3：选择、参数语义、检索、传输和拒答正确；模型没照抄 query，改写导致 baseline 精确分数/排名不同。同一实际query回放结果一致，原题query回放仍与冻结baseline一致。

## Latency
- Case 1：LLM1=23.867s；Tool完整执行=1.337s；LLM2=26.773s；E2E=53.276s
- Case 2：LLM1=21.514s；Tool完整执行=0.151s；LLM2=32.762s；E2E=54.427s
- Case 3（补测）：LLM1=37.205s；Tool完整执行=0.141s；LLM2=15.788s；E2E=54.140s
首个Tool执行包括惰性加载和线程启动；retriever内部embedding/FAISS耗时另见trace。LLM耗时到流完成，不只是HTTP headers。
Case3初始实验未写入第二轮latency，因此只修正观测时间戳并补测Case3，原始trace保留，补测见case3_retest.json。不得将不同运行耗时混为同一次测试。

## 保护和测试
37项既有RAG/评估测试 + 11项Phase2测试全部通过。36份RAG/插件/索引/资料/评估/配置指纹前后一致；nanobot Git clean。
初始三个case及补测case3均integration_success=true；不评价自主routing，不新增阈值，不修改system prompt进行重试优化。
可进入Phase3B；需将query改写与证据解释偏差列为评测事项。
