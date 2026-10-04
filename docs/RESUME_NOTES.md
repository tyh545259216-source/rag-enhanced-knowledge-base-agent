# Resume Notes

中文项目名：基于工具调用的本地检索增强知识库 Agent
英文项目名：RAG-Enhanced Knowledge Base Agent with Tool Calling
技术栈：Python、Ollama、Qwen3:1.7b、nomic-embed-text、FAISS、PyMuPDF、pytest、nanobot External Tools。

## 中文简历 bullet
- 基于两个MIT RAG实现做有来源记录的组件改编，统一PDF/TXT、fixed chunking、metadata与Retriever接口；使用L2归一化向量和FAISS IndexFlatIP。
- 通过nanobot.tools entry point将Retriever封装为只读search_knowledge_base，复用nanobot AgentRunner/ToolRegistry验证真实structured tool call及role=tool回传，不改框架core。
- 构建30题检索集、24题自主路由集；小规模自建测试上HitRate@3=100%、Recall@3=97.5%、MRR@3=0.925，路由Accuracy87.5%、F1 90.91%。
- 分层分析Routing/Retrieval/Generation/Policy失败，私有题核心正确率88.89%、严格groundedness83.33%；记录高相似度无答案与不实来源断言，不将小样本结果描述为生产性能。

## English bullets
- Adapted attributed MIT RAG components into a unified PDF/TXT retrieval pipeline with stable chunk metadata, normalized embeddings, and FAISS IndexFlatIP.
- Integrated a read-only knowledge search tool through nanobot's external entry point, reusing its AgentRunner and ToolRegistry for real structured calls and tool-result transport without modifying core.
- Built small custom datasets of 30 retrieval questions and 24 routing cases; measured Recall@3 of 97.5%, MRR@3 of 0.925, and routing F1 of 90.91% under a single-tool setup.
- Evaluated routing, evidence coverage, answer correctness and groundedness separately, retaining failure traces and documenting the limits of small, non-held-out datasets.

## 60秒介绍
我做的是一个用于学习的本地Agentic RAG项目。底层RAG改编自两个MIT项目，nanobot负责Agent运行时，我主要完成组件适配、统一Retriever、只读外部工具和分层评估。Qwen通过Ollama运行，模型自行决定查不查私有知识库；工具只检索，证据以role=tool返回后模型再生成答案。我用30道检索题和24道路由题建立baseline，检索Recall@3为97.5%，路由准确率87.5%。我特别区分检索和生成问题：例如资料同时有项目负责人、验收负责人，小模型会误判矛盾；无答案题也可能得到高相似度。因此我保留失败案例和原始trace，没有用阈值或改题隐藏问题。数据规模很小，这证明技术链路和基础自主路由，不代表生产可靠性。

## 5个面试追问
1. 普通LLM Chat与此Agent有何区别？——模型可返回structured tool_calls，框架执行并回传真实证据，再做第二次模型请求。
2. 为什么IndexFlatIP？——文档/query均L2归一化，内积近似余弦；维度从真实Embedding取，score不是正确率。
3. HitRate高为什么回答仍错？——命中不等于证据完整/正确理解，负责人角色误读是generation失败。
4. 无答案为何仍返回TopK？——近邻检索总排序；需要证据判断，当前未校准threshold，拒答和grounding分别评估。
5. 哪些原创，哪些复用？——复用nanobot runtime及带许可的RAG基础；项目完成适配、插件、接口与评估，来源commit和修改摘要可追踪。
