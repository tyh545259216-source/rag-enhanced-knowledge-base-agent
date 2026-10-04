# Third-party notices
上游原仓库未修改。vendor 代码是改编代码，不作为原创声明。

## rag-from-scratch
https://github.com/tajwarchy/rag-from-scratch
Commit: 4c4e039177ce2a7ac475339cff7a1187a6fd68bf
MIT，Copyright (c) 2026 Tajwar；完整声明见 licenses/rag-from-scratch-MIT.txt。
- core/extractor.py → vendor/rag_core/extractor.py：保留数字、相对路径、TXT。
- core/chunker.py:chunk_fixed/_make_chunk → vendor/rag_core/chunker.py：fixed、参数验证、稳定 ID。
- core/faiss_store.py → vendor/rag_core/faiss_store.py：IP、实例状态、显式路径、Unicode IO、一致性校验。

## ollama-local-rag-demo
https://github.com/fr3kchy/ollama-local-rag-demo
Commit: 2d4a5d30b4a4829a007b8132e11cea71282a83d7
MIT，Copyright (c) 2026 Michael Insch；完整声明见 licenses/ollama-local-rag-demo-MIT.txt。
- ingest.py:embed_texts + query.py:embed_query → vendor/ollama_embeddings.py：显式配置、统一归一化、拒绝无效向量。

## nanobot（外部运行时依赖）
https://github.com/HKUDS/nanobot
Commit: 66f5f2df15455b34fc22e656bdc1ef3d4f32e328
MIT，Copyright (c) 2025-present Xubin Ren and the nanobot contributors。
通过 nanobot.tools entry point 与 AgentRunner/ToolRegistry 集成；未复制或修改 nanobot core。完整许可证见 licenses/nanobot-MIT.txt。nanobot 需按固定 commit 单独安装，不属于本项目从零原创。
