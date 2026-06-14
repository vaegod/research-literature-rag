# 真实论文 Demo

本项目已验证可以导入真实 PDF，并基于真实论文进行问答、检索和引用溯源。

## 1. 示例论文

可以使用任意文本型科研论文 PDF，例如：

```text
<你的论文PDF路径>\Teaching Small Language Models Reasoning through.pdf
```

导入到项目后会保存为：

```text
data/raw_docs/teaching_small_language_models_reasoning.pdf
```

注意：真实论文 PDF 可能受版权或再分发协议限制。为了避免误提交，本项目默认忽略 `data/raw_docs/*.pdf`。开源到 GitHub 时，建议只保留导入说明，不直接提交论文 PDF，除非确认该 PDF 允许再分发。

## 2. 导入方式

### 前端导入

1. 启动服务：`uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload`
2. 打开 `http://127.0.0.1:8010/`
3. 在左侧上传 PDF
4. 上传成功后前端会自动重建索引
5. 在中间问答区选择 Agent 或 RAG 模式提问

### 命令行导入

也可以直接把 PDF 复制到 `data/raw_docs/`，然后重建索引：

```powershell
cd 科研文献智能问答
Copy-Item "<你的论文PDF路径>\Teaching Small Language Models Reasoning through.pdf" ".\data\raw_docs\teaching_small_language_models_reasoning.pdf"
.\.venv\Scripts\Activate.ps1
python scripts/build_index.py
```

## 3. 验证结果

本地构建索引后，示例 PDF 可生成约 75 个 chunk。实际数量会随 `CHUNK_SIZE`、`CHUNK_OVERLAP`、PDF 文本提取质量和切分规则变化。

适合测试的问题：

```text
这篇 Teaching Small Language Models Reasoning through... 的主要贡献是什么？
请总结这篇论文的方法流程。
这篇论文做了哪些实验，使用了哪些指标？
这篇论文有哪些局限或未来工作？
请基于这篇论文生成阅读笔记。
```

## 4. 为什么真实 PDF 更能体现项目价值

样例 Markdown 笔记更适合快速验证流程，但真实 PDF 会暴露更多真实问题：

- 页码、标题、参考文献和正文混在一起，检索更容易跑偏。
- 论文的贡献、方法、实验、局限分布在不同 section，需要更精细的检索策略。
- 引用来源需要返回页码和 chunk id，方便核查。
- PDF 文本抽取质量会影响 chunk 内容，需要在工程上留出定位与调试入口。

因此当前版本增加了 `section` 元数据和意图感知重排，让“主要贡献”“实验结果”“方法流程”等问题更容易命中正确区域。
