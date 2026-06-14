# RAG 应用开发笔记

## 基本概念

RAG 指 Retrieval-Augmented Generation，即检索增强生成。它通过外部知识库检索相关资料，再把检索结果和用户问题一起交给大模型生成答案。相比纯大模型问答，RAG 可以降低幻觉、提升知识更新能力，并让回答具备可追溯引用。

## 核心流程

一个典型 RAG 系统包含文档解析、文本清洗、chunk 切分、Embedding 向量化、向量库入库、检索、Prompt 拼接和答案生成。chunk_size 与 chunk_overlap 是影响效果的重要参数。chunk 太小会丢失上下文，chunk 太大则可能降低检索精度并增加 Prompt 成本。

## 检索设计

向量检索适合捕捉语义相似性，但对关键词、编号和精确术语可能不够敏感。因此在真实业务中常见的优化包括混合检索、metadata filter、query rewrite、rerank、parent-child chunk 和多查询检索。MVP 阶段可以先使用 FAISS 进行 TopK 向量检索，并返回文档名、页码和 chunk_id。

## Prompt 约束

RAG Prompt 需要明确要求模型依据参考资料回答，资料不足时说明无法确认，不要编造文献结论或实验数值。回答最好包含直接结论、依据说明和引用来源。引用来源不仅提升可信度，也方便开发者排查检索是否命中了正确文档。

## 评测方法

RAG 评测可以从 source_hit_rate、keyword_hit_rate、faithfulness 和 latency 等维度进行。MVP 阶段可以维护一个测试问题 CSV，每条问题包含预期来源和关键词。评测脚本批量调用 Agent 后，统计来源命中、关键词覆盖和平均耗时，再根据失败样例调整 TopK、chunk_size、overlap 和 Prompt。
