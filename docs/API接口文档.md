# API 接口文档

服务默认启动在 `http://127.0.0.1:8010`。

## GET /health

健康检查。除服务版本外，还会返回是否配置 API Key、FAISS 索引是否存在、源文档数量和当前 chunk 数量。

```json
{
  "status": "ok",
  "service": "research-literature-rag-agent",
  "version": "0.1.0",
  "has_api_key": true,
  "index_exists": true,
  "raw_doc_count": 6,
  "chunk_count": 83
}
```

## POST /documents/upload

上传 PDF、Markdown 或 TXT 文档。空文件会被拒绝，默认最大 20MB，同名文件会自动追加序号，避免覆盖已有源文档。

响应中的 `index_status=stale` 表示源文档已变化，调用方需要继续调用 `/knowledge/build`。Web 控制台会自动触发该同步。

## GET /documents

查看源文档列表，包含文件名、大小、修改时间、chunk 数量和是否可编辑。

## POST /documents

创建 Markdown 或 TXT 文档。成功后返回 `index_status=stale`。

```json
{
  "filename": "new_note.md",
  "content": "# 新笔记\n\n这里写文献笔记。"
}
```

## GET /documents/{filename}

读取单个源文档内容。Markdown 和 TXT 可编辑，PDF 只读。

## PUT /documents/{filename}

更新 Markdown 或 TXT 文档内容。成功后返回 `index_status=stale`。

```json
{
  "content": "# 更新后的内容"
}
```

## DELETE /documents/{filename}

删除源文档。成功后返回 `index_status=stale`。

## GET /documents/chunks

查看所有已切分 chunk，可传 `query` 和 `limit`。

```text
/documents/chunks?query=LoRA&limit=20
```

## GET /documents/{filename}/chunks

查看某个文档对应的 chunk。

```text
/documents/lora_finetuning_notes.md/chunks?limit=20
```

## POST /knowledge/build

构建 FAISS 知识库。

```json
{
  "force_rebuild": true
}
```

## POST /knowledge/search

检索知识库。默认使用 FAISS dense + BM25 hybrid 召回，并根据问题意图做 section rerank。若 `.env` 中 `ENABLE_RERANKER=true`，会额外调用 SiliconFlow `/rerank` 对候选 chunk 做二阶段精排。

```json
{
  "query": "LoRA 为什么能减少训练参数？",
  "top_k": 4
}
```

返回结果的 `metadata` 中会包含调试字段，例如 `retrieval_channels`、`dense_score`、`bm25_score`、`hybrid_score`、`section_adjusted_score`、`rerank_score` 和 `ranker`，便于排查结果来自 dense、BM25、hybrid 还是 SiliconFlow reranker。

## POST /chat/rag

执行普通 RAG 问答。

```json
{
  "question": "知识蒸馏的核心思想是什么？",
  "top_k": 4
}
```

## POST /chat/rag/stream

执行流式 RAG 问答，返回 `text/event-stream`。事件顺序如下：

| event | data | 说明 |
| --- | --- | --- |
| `meta` | `sources`, `related_chunks` | 先返回引用来源和检索片段，便于前端立即展示检索证据 |
| `delta` | `text` | 模型增量输出 |
| `done` | `{}` | 生成完成 |
| `error` | `message` | 生成阶段失败 |

请求体与 `/chat/rag` 一致：

```json
{
  "question": "RAG 为什么要返回引用来源？",
  "top_k": 4
}
```

## POST /chat/agent

执行 Agent 问答，由 LangGraph 路由到具体工具。默认使用规则路由；设置 `AGENT_ROUTER_MODE=hybrid` 或 `llm` 后可启用可选 LLM Router。响应的 `tool_result` 中会包含 `router`、`router_confidence` 和 `router_reason`。

```json
{
  "question": "查询 EXP-003 的实验结果。",
  "top_k": 4
}
```

## POST /experiments/search

查询实验记录。

```json
{
  "query": "EXP-003"
}
```

## POST /eval/run

运行评测。响应中包含来源命中率、关键词命中率、Recall@K、MRR、平均耗时和失败样例。

```json
{
  "limit": 5
}
```
