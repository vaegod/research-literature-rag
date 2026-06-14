# Changelog

## 0.2.0 - Unreleased

- 增加 RAG 流式回答接口 `/chat/rag/stream`，前端支持 SSE 增量展示。
- 增加检索调试面板，展示 dense、BM25、hybrid、section、ranker 等元数据。
- 评测集增加 `expected_chunk_ids`，评测说明新增 Recall@K 和 MRR。
- CORS、应用版本、FAISS 本地索引信任边界改为环境变量配置。
- 补齐开源项目文件、Issue/PR 模板、Dependabot 和发布审计脚本。

## 0.1.0 - Initial

- FastAPI + LangChain + LangGraph + FAISS 的科研文献 RAG MVP。
- 支持 PDF/Markdown/TXT 文档上传、切分、索引构建、RAG 问答、Agent 路由、实验记录查询和评测闭环。
