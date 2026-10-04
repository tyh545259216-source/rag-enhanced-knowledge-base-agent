# Phase 2 — 外部只读 Tool 验证
插件：src/knowledge_base_agent/tools/search_knowledge_base.py。
安装在 nanobot .venv：python -m pip install --no-deps -e <PROJECT_ROOT>。
仅新增缺失 NumPy 2.5.3、faiss-cpu 1.15.1、PyMuPDF 1.28.2；无已有依赖升级。
entry point group=nanobot.tools；通过实际 ToolLoader.load 和 ToolRegistry 验证。
query 必填，top_k 默认3、范围1..10；超上限返回 invalid_arguments；大于 ntotal 由冻结 Retriever 裁剪。
默认配置为 editable 项目 config.yaml；可用 KNOWLEDGE_BASE_CONFIG 指定独立配置绝对路径，不修改 nanobot config。
索引惰性只读加载。线程中调用 Retriever，同实例串行；不生成回答，不使用阈值。
结果为 ToolResult(JSON)，正常 is_error=False；参数、索引/metadata、Embedding 错误返回 is_error=True。
测试：nanobot .venv 中 python -B <PROJECT_ROOT>\phase2\test_tool.py，11通过。
现有测试：knowledge-base-agent .venv pytest tests -q，37通过。
冻结文件运行前后33份 SHA256 一致；nanobot git status --porcelain 无输出。
实际 schema、直接工具结果、依赖及指纹验证见本目录 JSON。
尚未启动或重启 Gateway。新 Gateway 进程会扫描安装的 entry point；现有进程不会因此自动刷新缓存。
没有运行 Qwen Tool Calling 或 Agent Routing，接入能力已验证，模型是否选对工具仍待下一阶段真实验证。
