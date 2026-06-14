# Contributing

感谢关注这个项目。这个仓库定位为一个可复现、可扩展的科研文献 RAG 工程样例，因此贡献优先关注三类价值：

- 提升检索、生成、评测的可解释性。
- 提升本地启动、Docker、CI 的可复现性。
- 修正文档、示例和代码之间的不一致。

## 本地开发

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

配置 `.env` 后可构建索引并启动服务：

```powershell
python scripts/build_index.py
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

## 提交前检查

```powershell
.\scripts\check.ps1
```

该脚本会运行仓库审计、Ruff 和 Pytest。没有 Docker 环境时，可以只运行：

```powershell
python scripts/open_source_audit.py
ruff check .
python -m pytest
```

## Pull Request 建议

- 保持 PR 聚焦，一个 PR 只解决一个主题。
- 如果改动检索、重排或 Prompt，请补充测试或评测样例。
- 如果改动 README 或文档，请确认代码实际行为与描述一致。
- 不要提交 `.env`、`.venv/`、FAISS 索引、chunk 中间文件、日志、真实论文 PDF。

## 代码风格

项目使用 Ruff 做基础检查，Python 目标版本为 3.13。代码应尽量保持简单清晰，避免引入不必要抽象。
