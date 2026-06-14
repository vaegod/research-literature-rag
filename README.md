# 科研文献智能问答与实验分析助手

![Python](https://img.shields.io/badge/Python-3.13-245a9b)
![FastAPI](https://img.shields.io/badge/FastAPI-RAG%20API-1e6b4f)
![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-a34724)
![CI](https://img.shields.io/badge/CI-pytest%20%7C%20ruff%20%7C%20docker-202826)
![License](https://img.shields.io/badge/License-MIT-f1c76a)

面向论文阅读、实验记录查询和小规模科研知识库管理的 RAG 应用。系统使用 FastAPI 提供后端接口，基于 LangChain 完成文档解析、切分、向量化和 FAISS 检索，结合 BM25 混合召回、章节感知重排和可选 reranker 提升检索质量，并通过 LangGraph 编排文献问答、论文对比、实验查询和阅读笔记生成等多意图流程。

项目关注的不只是一次问答结果，而是一个可复现的科研资料处理链路：文档上传、知识库构建、检索增强问答、引用溯源、实验记录查询、评测反馈和工程化交付。

![Web 控制台预览](docs/assets/console-preview.png)

## 核心能力

- **证据可追溯**：回答返回统一引用来源，前端同步展示相关 chunk、页码、来源文件和检索调试信息。
- **检索可解释**：dense、BM25、RRF hybrid、section rerank 和可选 reranker 的关键分数会写入 metadata。
- **流程可编排**：LangGraph 将文献问答、论文对比、实验记录查询、阅读笔记生成和普通问答组织为清晰的多意图工作流。
- **评测可迭代**：评测集支持 `expected_source`、`expected_keywords` 和 `expected_chunk_ids`，输出 source hit、keyword hit、Recall@K、MRR 和失败样例。
- **交付可复现**：提供 Pytest、Ruff、敏感文件检查脚本、Docker build、GitHub Actions、Dependabot 和本地运行脚本。
- **界面可操作**：Web 控制台支持文档管理、RAG/Agent/Search 模式、流式 RAG 输出、引用来源和检索链路展示。

## 功能概览

- 文献知识库：支持 PDF、Markdown、TXT 上传；调用重建接口后自动解析、切分、向量化并写入本地 FAISS。
- RAG 问答：通过 dense embedding + BM25 混合召回、section rerank 和可选 SiliconFlow reranker 检索 TopK 片段，再调用 Chat 模型生成带来源的回答。
- 流式输出：`/chat/rag/stream` 使用 SSE 先返回引用和 chunk，再持续推送模型增量文本。
- Agent 工作流：使用 LangGraph 编排文献问答、论文对比、实验记录查询、阅读笔记生成和普通问答；默认规则路由，可通过环境变量启用可选 LLM Router。
- 知识库管理：前端支持查看源文档、浏览 chunk、创建/编辑/删除 Markdown/TXT 文档；Web 控制台在文档变更后会调用重建索引接口。
- 检索调试：前端展示 dense/BM25/hybrid/rerank 分数、section、ranker 和来源通道，便于定位检索命中原因。
- 评测闭环：维护评测问题集，输出来源命中率、关键词命中率、Recall@K、MRR、平均耗时和失败样例。
- 工程交付：提供 Pytest、Ruff、敏感文件检查、评测集一致性检查、Swagger、Docker Compose、GitHub Actions CI 和 Dependabot。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| Web/API | FastAPI, Pydantic, Uvicorn |
| RAG | LangChain, FAISS, BM25, OpenAI-compatible Embeddings, SiliconFlow Rerank |
| Agent | LangGraph |
| LLM Provider | SiliconFlow OpenAI 兼容接口 |
| 前端 | 原生 HTML/CSS/JavaScript |
| 测试 | Pytest, FastAPI TestClient, coverage |
| 工程化 | Ruff, Docker, Docker Compose, GitHub Actions, Dependabot |

## 架构

```mermaid
flowchart LR
    User["用户 / 前端控制台"] --> API["FastAPI API"]
    API --> DocAPI["文档管理接口"]
    API --> RagAPI["RAG/Agent 问答接口"]
    API --> EvalAPI["评测接口"]

    DocAPI --> Loader["PDF/MD/TXT Loader"]
    Loader --> Splitter["Recursive Splitter + section metadata"]
    Splitter --> Embedding["Embedding Model"]
    Embedding --> FAISS["FAISS 本地向量索引"]

    RagAPI --> Retriever["BM25 + Dense Hybrid Retrieval + Section/Reranker"]
    Retriever --> FAISS
    Retriever --> Chat["Chat Model"]
    Chat --> Answer["答案 + Sources + Related Chunks"]

    RagAPI --> Graph["LangGraph Workflow"]
    Graph --> Literature["文献问答"]
    Graph --> Compare["论文对比"]
    Graph --> Experiment["实验记录查询"]
    Graph --> Notes["阅读笔记生成"]
    Graph --> General["普通问答"]

    Experiment --> ExpJSON["data/experiments/*.json"]
    EvalAPI --> EvalCSV["data/eval/rag_eval_questions.csv"]
```

更完整的模块说明见 [docs/项目架构.md](docs/项目架构.md) 和 [docs/科研文献智能问答与实验分析助手_开发文档.md](docs/科研文献智能问答与实验分析助手_开发文档.md)。

## 目录结构

```text
科研文献智能问答/
├─ app/
│  ├─ api/              # FastAPI 路由
│  ├─ chains/           # RAG、对比、笔记、普通问答链
│  ├─ graph/            # LangGraph 状态、节点和工作流
│  ├─ retriever/        # 文档加载、切分、向量库、检索重排
│  ├─ services/         # 业务服务封装
│  ├─ static/           # 前端控制台
│  └─ tools/            # Agent 工具
├─ data/
│  ├─ raw_docs/         # 本地知识库源文档
│  ├─ processed_docs/   # chunk 中间产物，默认不提交
│  ├─ experiments/      # 实验记录 JSON
│  └─ eval/             # 评测问题与结果
├─ docs/                # 架构、API、评测、示例和维护说明
├─ scripts/             # 构建索引、评测、Demo 查询
├─ tests/               # 单元测试和 API schema 测试
└─ vector_store/        # FAISS 索引，默认不提交
```

## 快速体验

1. 安装依赖并复制 `.env.example` 为 `.env`。
2. 填入 OpenAI-compatible API Key。
3. 运行 `python scripts/build_index.py` 构建样例知识库。
4. 运行 `uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload`。
5. 打开 `http://127.0.0.1:8010/`，选择 RAG 模式并提问：`RAG 为什么要返回引用来源？`
6. 查看右侧引用来源、相关片段和检索调试面板，确认答案证据链。

## 快速启动

### 0. Windows 脚本启动

如果已经创建好 `.venv` 并安装依赖，可以直接双击项目根目录下的：

```text
启动项目.bat
```

脚本会在后台启动 FastAPI 服务，并打开：

```text
http://127.0.0.1:8010/
```

如果 8010 端口上已经有服务运行，脚本会直接打开页面。停止服务时双击：

```text
停止项目.bat
```

### 1. 本地运行

```powershell
cd 科研文献智能问答
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，填入模型服务密钥：

```env
APP_VERSION=0.1.0
OPENAI_COMPATIBLE_API_KEY=your_api_key
OPENAI_COMPATIBLE_BASE_URL=https://api.siliconflow.cn/v1
CHAT_MODEL=deepseek-ai/DeepSeek-V3
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
CORS_ALLOW_ORIGINS=http://127.0.0.1:8010,http://localhost:8010
CORS_ALLOW_CREDENTIALS=false
DEFAULT_TOP_K=4
CHUNK_SIZE=800
CHUNK_OVERLAP=120
MAX_UPLOAD_SIZE_MB=20
RETRIEVAL_MODE=hybrid
ENABLE_RERANKER=false
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
AGENT_ROUTER_MODE=rule
TRUST_LOCAL_FAISS_INDEX=true
```

默认使用本地 BM25 + FAISS dense 混合召回。需要调用硅基流动 rerank API 时，将 `.env` 中的 `ENABLE_RERANKER` 设为 `true`，默认 reranker 模型为 `BAAI/bge-reranker-v2-m3`。

`TRUST_LOCAL_FAISS_INDEX=true` 表示只加载本项目在本机生成的 FAISS 索引。不要加载陌生来源的 `index.pkl`。

构建知识库并启动服务：

```powershell
python scripts/build_index.py
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

访问入口：

- Web 控制台：`http://127.0.0.1:8010/`
- Swagger API 文档：`http://127.0.0.1:8010/docs`
- 健康检查：`http://127.0.0.1:8010/health`

退出服务：在启动服务的终端按 `Ctrl + C`。

### 2. Docker Compose 运行

```powershell
cd 科研文献智能问答
Copy-Item .env.example .env
docker compose up --build
```

停止服务：

```powershell
docker compose down
```

Docker Compose 会挂载本地 `data/raw_docs/`、`data/processed_docs/` 和 `vector_store/faiss_index/`，便于保留上传文档和索引。

## Web 控制台

Web 控制台默认位于 `http://127.0.0.1:8010/`，包含三块主要区域：

- 左侧运行区：上传文档、重建索引、运行评测、查看服务状态。
- 中间问答区：在 Agent、RAG、Search 三种模式之间切换，可多次提交问题，并展示回答耗时；RAG 模式可开启流式输出。
- 右侧知识库区：查看源文档、编辑 Markdown/TXT、删除文档、查看所有 chunk、当前回答引用来源和检索调试链路。

增删改源文档后，前端会调用 `/knowledge/build` 同步索引。直接调用后端 CRUD API 时，接口会返回 `index_status=stale`，调用方需要显式触发 `/knowledge/build`。PDF 只读，Markdown/TXT 可直接编辑。

## API 摘要

| 接口 | 说明 |
| --- | --- |
| `GET /health` | 服务健康检查，包含 API Key、索引和文档状态 |
| `POST /documents/upload` | 上传 PDF/Markdown/TXT |
| `GET /documents` | 查看源文档列表 |
| `POST /documents` | 新建 Markdown/TXT 文档 |
| `GET /documents/{filename}` | 读取文档内容 |
| `PUT /documents/{filename}` | 更新 Markdown/TXT 文档 |
| `DELETE /documents/{filename}` | 删除源文档并返回索引过期状态 |
| `GET /documents/chunks` | 查看已切分 chunk |
| `POST /knowledge/build` | 构建 FAISS 知识库 |
| `POST /knowledge/search` | TopK 检索 |
| `POST /chat/rag` | 普通 RAG 问答 |
| `POST /chat/rag/stream` | SSE 流式 RAG 问答 |
| `POST /chat/agent` | Agent 工作流问答 |
| `POST /experiments/search` | 查询实验记录 |
| `POST /eval/run` | 运行评测 |

完整请求示例见 [docs/API接口文档.md](docs/API接口文档.md)。

## RAG 与 Agent 流程

1. 文档加载：PDF 通过 `pypdf` 提取页级文本，Markdown/TXT 直接读取。
2. 文本切分：使用 `RecursiveCharacterTextSplitter`，按标题、段落、句号、逗号和空格递归切分，默认 `chunk_size=800`、`chunk_overlap=120`。
3. 元数据增强：为 chunk 注入 `source`、`page`、`doc_id`、`chunk_id`、`section` 等字段。
4. 向量化：调用 OpenAI 兼容 Embedding 接口，将 chunk 转成向量。
5. 检索：FAISS dense 检索召回语义候选，BM25 从 `chunks.jsonl` 做关键词候选召回，两路结果按归一化分数和 RRF 融合。
6. 精排：根据问题意图做 section rerank，例如主要贡献优先 Abstract/Introduction，实验问题优先 Experiments/Results；开启 `ENABLE_RERANKER=true` 后，再调用 SiliconFlow `/rerank` 做二阶段精排。
7. 调试：检索结果 metadata 保留 dense、BM25、hybrid、section adjusted、reranker 等分数，前端可直接展示排序链路。
8. 生成：把检索片段作为上下文输入 Chat 模型，要求答案基于资料，并在返回后由系统补齐统一编号的引用来源；RAG 模式支持 SSE 流式输出。
9. 路由：LangGraph 先识别意图，再进入文献问答、论文对比、实验查询、笔记生成或普通问答节点；默认使用规则路由，设置 `AGENT_ROUTER_MODE=hybrid` 或 `llm` 后可启用模型路由兜底。

## 示例问题

```text
这篇 Teaching Small Language Models Reasoning through... 的主要贡献是什么？
请总结这篇论文的方法流程。
这篇论文做了哪些实验，使用了哪些指标？
对比 LoRA 和知识蒸馏的区别。
查询 EXP-003 的实验结果。
生成一份 RAG 应用开发笔记的阅读笔记。
```

## 问答示例

下面是导入真实论文后的一次 Agent 问答示例。页面左侧展示运行状态和评测入口，中间展示问题与回答，右侧展示源文档、chunk 和引用证据。

![真实论文问答示例](docs/assets/qa-example-focused.png)

## 评测

```powershell
python scripts/run_eval.py
python scripts/run_eval.py --limit 5
```

评测集位于 `data/eval/rag_eval_questions.csv`，覆盖 `data/raw_docs/` 中的样例笔记、实验记录和普通问答兜底。结果输出到 `data/eval/eval_result.csv`，该文件属于本地运行产物，默认不提交。指标包括：

- `source_hit_rate`：回答或工具结果是否命中预期来源。
- `keyword_hit_rate`：回答是否覆盖预期关键词，默认命中一半以上关键词视为通过。
- `retrieval_recall_at_k`：有 gold chunk 的问题中，TopK 是否召回预期片段。
- `mean_reciprocal_rank`：第一个 gold chunk 排名倒数的平均值。
- `avg_latency`：平均响应耗时。
- `failed_cases`：保留失败样例，便于继续优化检索、Prompt 和切分策略。

详细说明见 [docs/评测说明.md](docs/评测说明.md)。

## 数据说明

- `data/raw_docs/*.md` 是用于验证 RAG 流程的样例笔记，不代表真实论文原文。
- 真实论文 PDF 默认保留在本地，除非确认具有可再分发许可。本项目已默认忽略 `data/raw_docs/*.pdf`。
- `.env`、`.venv/`、FAISS 索引、chunk 中间文件、评测输出和真实 PDF 默认不纳入版本控制。
- 上传接口默认限制单文件最大 20MB，空文件会被拒绝，同名文件会自动追加序号避免覆盖。
- 项目使用 MIT License；可运行 `python scripts/open_source_audit.py` 检查敏感文件和常见密钥形态。

更多说明见 [docs/仓库维护说明.md](docs/仓库维护说明.md) 和 [docs/实现边界说明.md](docs/实现边界说明.md)。

## 测试与质量检查

```powershell
.\.venv\Scripts\python.exe -m pytest
```

无 API Key 场景下，测试通过 mock 覆盖 health、loader、retrieval、RAG、Agent 路由、API schema 和评测集来源一致性。

本地提交前可运行：

```powershell
pip install -r requirements-dev.txt
.\scripts\check.ps1
```

CI 会执行：

- `python scripts/open_source_audit.py`：检查敏感文件是否被跟踪，并扫描常见密钥形态。
- `ruff check .`：静态检查和导入排序。
- `python -m pytest --cov=app --cov-report=term-missing`：单测和覆盖率报告。
- `pip-audit -r requirements.txt`：依赖漏洞审计，CI 中作为信息项。
- `docker build .`：验证镜像可构建。

## Roadmap

- 接入真实论文元数据解析：标题、作者、摘要、DOI、发表年份。
- 增加多轮记忆：支持基于会话的连续追问和引用继承。
- 增加用户级知识库隔离：为多用户或多项目场景准备权限边界。
- 支持 OCR、论文表格/图片解析和跨文档 evidence graph。
