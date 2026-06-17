const state = {
  mode: "agent",
  selectedDocument: null,
};

const $ = (selector) => document.querySelector(selector);

function setBusy(button, busyText) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = busyText;
  return () => {
    button.disabled = false;
    button.textContent = original;
  };
}

function addLog(message) {
  const log = $("#log");
  const line = document.createElement("div");
  line.className = "log-line";
  line.textContent = `${new Date().toLocaleTimeString()}  ${message}`;
  log.prepend(line);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderAnswer(text) {
  const target = $("#answer");
  const value = text || "没有返回答案。";
  target.dataset.raw = value;
  target.innerHTML = renderMarkdown(value);
}

function appendAnswer(text) {
  const target = $("#answer");
  const value = `${target.dataset.raw || ""}${text || ""}`;
  target.dataset.raw = value;
  target.innerHTML = renderMarkdown(value || "正在生成...");
}

function renderInlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[S(\d+)\]/g, '<span class="citation">[S$1]</span>');
}

function splitTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isTableSeparator(line) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function renderMarkdown(text) {
  const lines = String(text).replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let paragraph = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    html.push(`<p>${paragraph.map(renderInlineMarkdown).join("<br>")}</p>`);
    paragraph = [];
  };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      flushParagraph();
      continue;
    }

    if (trimmed.startsWith("```")) {
      flushParagraph();
      const codeLines = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i += 1;
      }
      html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
      continue;
    }

    if (trimmed.includes("|") && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      flushParagraph();
      const headers = splitTableRow(trimmed);
      const rows = [];
      i += 2;
      while (i < lines.length && lines[i].trim().includes("|")) {
        rows.push(splitTableRow(lines[i]));
        i += 1;
      }
      i -= 1;
      html.push(
        `<table><thead><tr>${headers
          .map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`)
          .join("")}</tr></thead><tbody>${rows
          .map(
            (row) =>
              `<tr>${row.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join("")}</tr>`
          )
          .join("")}</tbody></table>`
      );
      continue;
    }

    const heading = /^(#{1,3})\s+(.+)$/.exec(trimmed);
    if (heading) {
      flushParagraph();
      const level = heading[1].length + 2;
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      flushParagraph();
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
        i += 1;
      }
      i -= 1;
      html.push(`<ul>${items.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</ul>`);
      continue;
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      flushParagraph();
      const items = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
        i += 1;
      }
      i -= 1;
      html.push(`<ol>${items.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</ol>`);
      continue;
    }

    paragraph.push(line);
  }

  flushParagraph();
  return html.join("");
}

function markIndexStale(data) {
  if (data?.index_status === "stale") {
    $("#knowledgeHint").textContent = "源文档已变更，正在自动同步索引...";
  }
}

function renderSources(sources = []) {
  $("#sourceCount").textContent = sources.length;
  const target = $("#sources");
  if (!sources.length) {
    target.className = "source-list empty";
    target.textContent = "暂无引用。";
    return;
  }
  target.className = "source-list";
  target.innerHTML = sources
    .map((source) => {
      const page = source.page ? `第 ${source.page} 页` : "页码未记录";
      const chunk = source.chunk_id ? ` · ${source.chunk_id}` : "";
      return `<div class="source-item"><div class="source-title">${escapeHtml(
        source.source
      )}</div><div>${escapeHtml(page + chunk)}</div></div>`;
    })
    .join("");
}

function renderChunks(chunks = []) {
  $("#chunkCount").textContent = chunks.length;
  renderRetrievalDebug(chunks);
  const target = $("#chunks");
  if (!chunks.length) {
    target.className = "chunk-list empty";
    target.textContent = "暂无片段。";
    return;
  }
  target.className = "chunk-list";
  target.innerHTML = chunks
    .map((chunk) => {
      const score = typeof chunk.score === "number" ? `score=${chunk.score.toFixed(3)}` : "";
      const parser = formatParser(chunk.metadata || {});
      const text = escapeHtml(chunk.content || "").slice(0, 420);
      return `<div class="chunk-item"><mark>${escapeHtml(chunk.source || "unknown")}</mark> ${escapeHtml(
        score
      )} · parser=${escapeHtml(parser)}<br>${text}</div>`;
    })
    .join("");
}

function formatScore(value) {
  return typeof value === "number" ? value.toFixed(3) : "n/a";
}

function formatParser(metadata = {}) {
  if (metadata.parser) return metadata.parser;
  if (metadata.file_type === "pdf") return "pypdf";
  return metadata.file_type || "text";
}

function renderRetrievalDebug(chunks = []) {
  const target = $("#retrievalDebug");
  if (!chunks.length) {
    target.className = "debug-list empty";
    target.textContent = "暂无检索链路。";
    return;
  }
  target.className = "debug-list";
  target.innerHTML = chunks
    .map((chunk, index) => {
      const meta = chunk.metadata || {};
      const channels = Array.isArray(meta.retrieval_channels)
        ? meta.retrieval_channels.join(" + ")
        : meta.ranker || "dense";
      const section = meta.section || "body";
      const ranker = meta.ranker || "dense";
      return `<div class="debug-item">
        <div class="debug-head">
          <strong>#${index + 1} ${escapeHtml(chunk.source || "unknown")}</strong>
          <span>${escapeHtml(channels)}</span>
        </div>
        <div class="debug-grid">
          <span>ranker</span><b>${escapeHtml(ranker)}</b>
          <span>section</span><b>${escapeHtml(section)}</b>
          <span>dense</span><b>${escapeHtml(formatScore(meta.dense_score))}</b>
          <span>bm25</span><b>${escapeHtml(formatScore(meta.bm25_score))}</b>
          <span>hybrid</span><b>${escapeHtml(formatScore(meta.hybrid_score ?? chunk.score))}</b>
          <span>final</span><b>${escapeHtml(formatScore(chunk.score))}</b>
        </div>
      </div>`;
    })
    .join("");
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

async function checkHealth() {
  const dot = $("#healthDot");
  const text = $("#healthText");
  try {
    const data = await requestJson("/health");
    dot.className = "status-dot ok";
    const indexStatus = data.index_exists ? `${data.chunk_count} chunks` : "索引未构建";
    const keyStatus = data.has_api_key ? "Key 已配置" : "Key 未配置";
    text.textContent = `${data.status} · ${data.raw_doc_count} docs · ${indexStatus} · ${keyStatus}`;
    const parserBadge = $("#parserBadge");
    const parser = data.pdf_parser || "pypdf";
    const mineruReady = data.mineru_enabled && data.mineru_has_token;
    const parserText =
      parser === "mineru"
        ? `PDF 解析器：MinerU ${data.mineru_model_version || ""}`.trim()
        : "PDF 解析器：pypdf";
    parserBadge.textContent =
      data.mineru_enabled && !data.mineru_has_token
        ? "PDF 解析器：MinerU 未配置 Token"
        : parserText;
    parserBadge.className = `parser-badge${mineruReady ? " active" : ""}${
      data.mineru_enabled && !data.mineru_has_token ? " warn" : ""
    }`;
  } catch (error) {
    dot.className = "status-dot bad";
    text.textContent = "服务异常";
    $("#parserBadge").textContent = "PDF 解析器：状态未知";
    $("#parserBadge").className = "parser-badge warn";
  }
}

async function uploadDocument() {
  const input = $("#fileInput");
  const file = input.files[0];
  if (!file) {
    addLog("请先选择一个文档。");
    return;
  }
  const done = setBusy($("#uploadBtn"), "上传中");
  try {
    const body = new FormData();
    body.append("file", file);
    const response = await fetch("/documents/upload", { method: "POST", body });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    addLog(`已上传 ${data.filename}`);
    markIndexStale(data);
    await loadDocuments();
    await rebuildAfterMutation(`上传 ${data.filename}`);
  } catch (error) {
    addLog(`上传失败：${error.message}`);
  } finally {
    done();
  }
}

async function buildKnowledge({ reason = "手动重建", silent = false } = {}) {
  const done = setBusy($("#buildBtn"), "同步中");
  try {
    if (!silent) {
      addLog(`${reason}：开始同步向量索引。`);
    }
    $("#knowledgeHint").textContent = "正在同步索引，请稍候...";
    const data = await requestJson("/knowledge/build", {
      method: "POST",
      body: JSON.stringify({ force_rebuild: true }),
    });
    addLog(`索引完成：${data.loaded_documents} 个文档，${data.generated_chunks} 个片段。`);
    $("#knowledgeHint").textContent = `索引已更新：${data.generated_chunks} 个片段。`;
    await loadDocuments();
    await loadChunks(state.selectedDocument);
    return data;
  } catch (error) {
    addLog(`构建失败：${error.message}`);
    $("#knowledgeHint").textContent = "源文档已变更，但索引同步失败。请检查 API Key 或网络后手动重建。";
    throw error;
  } finally {
    done();
  }
}

async function rebuildAfterMutation(reason) {
  try {
    await buildKnowledge({ reason, silent: true });
  } catch {
    // buildKnowledge already reports the failure in the UI.
  }
}

function formatSize(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function renderDocuments(documents = []) {
  const target = $("#docList");
  if (!documents.length) {
    target.className = "doc-list empty";
    target.textContent = "暂无文档。";
    return;
  }
  target.className = "doc-list";
  target.innerHTML = documents
    .map((doc) => {
      const active = doc.filename === state.selectedDocument ? " active" : "";
      const editable = doc.editable ? "可编辑" : "只读";
      return `<button class="doc-item${active}" data-filename="${escapeHtml(doc.filename)}">
        <span class="doc-name">${escapeHtml(doc.filename)}</span>
        <span class="doc-meta">${escapeHtml(doc.file_type.toUpperCase())} · ${formatSize(
          doc.size
        )} · ${doc.chunk_count} chunks · ${editable}</span>
      </button>`;
    })
    .join("");

  document.querySelectorAll(".doc-item").forEach((button) => {
    button.addEventListener("click", () => selectDocument(button.dataset.filename));
  });
}

async function loadDocuments() {
  try {
    const data = await requestJson("/documents");
    renderDocuments(data.documents || []);
    if (!state.selectedDocument && data.documents?.length) {
      await selectDocument(data.documents[0].filename);
    }
  } catch (error) {
    $("#docList").className = "doc-list empty";
    $("#docList").textContent = `读取失败：${error.message}`;
  }
}

async function selectDocument(filename) {
  state.selectedDocument = filename;
  $("#docFilename").value = filename;
  await loadDocumentsWithoutAutoSelect();

  try {
    const data = await requestJson(`/documents/${encodeURIComponent(filename)}`);
    $("#docEditor").value = data.editable ? data.content : data.message;
    $("#docEditor").disabled = !data.editable;
    addLog(`已打开 ${filename}`);
    await loadChunks(filename);
  } catch (error) {
    addLog(`读取文档失败：${error.message}`);
  }
}

async function loadDocumentsWithoutAutoSelect() {
  const current = state.selectedDocument;
  try {
    const data = await requestJson("/documents");
    state.selectedDocument = current;
    renderDocuments(data.documents || []);
  } catch {
    state.selectedDocument = current;
  }
}

async function createDocumentFromEditor() {
  const filename = $("#docFilename").value.trim();
  if (!filename) {
    addLog("请输入新文档文件名。");
    return;
  }
  const done = setBusy($("#newDocBtn"), "新增中");
  try {
    const data = await requestJson("/documents", {
      method: "POST",
      body: JSON.stringify({ filename, content: $("#docEditor").value }),
    });
    addLog(data.message);
    markIndexStale(data);
    state.selectedDocument = data.filename;
    await loadDocuments();
    await selectDocument(data.filename);
    await rebuildAfterMutation(`新增 ${data.filename}`);
  } catch (error) {
    addLog(`新增失败：${error.message}`);
  } finally {
    done();
  }
}

async function saveSelectedDocument() {
  const filename = state.selectedDocument || $("#docFilename").value.trim();
  if (!filename) {
    addLog("请先选择或新增文档。");
    return;
  }
  const done = setBusy($("#saveDocBtn"), "保存中");
  try {
    const data = await requestJson(`/documents/${encodeURIComponent(filename)}`, {
      method: "PUT",
      body: JSON.stringify({ content: $("#docEditor").value }),
    });
    addLog(data.message);
    markIndexStale(data);
    await loadDocuments();
    await rebuildAfterMutation(`保存 ${data.filename}`);
  } catch (error) {
    addLog(`保存失败：${error.message}`);
  } finally {
    done();
  }
}

async function deleteSelectedDocument() {
  const filename = state.selectedDocument;
  if (!filename) {
    addLog("请先选择要删除的文档。");
    return;
  }
  if (!confirm(`确定删除 ${filename}？删除后会自动同步索引。`)) {
    return;
  }
  const done = setBusy($("#deleteDocBtn"), "删除中");
  try {
    const data = await requestJson(`/documents/${encodeURIComponent(filename)}`, {
      method: "DELETE",
    });
    addLog(data.message);
    markIndexStale(data);
    state.selectedDocument = null;
    $("#docFilename").value = "";
    $("#docEditor").value = "";
    $("#docEditor").disabled = false;
    await loadDocuments();
    await loadChunks(null);
    await rebuildAfterMutation(`删除 ${data.filename}`);
  } catch (error) {
    addLog(`删除失败：${error.message}`);
  } finally {
    done();
  }
}

function renderLibraryChunks(chunks = [], total = 0) {
  const target = $("#libraryChunks");
  if (!chunks.length) {
    target.className = "library-chunks empty";
    target.textContent = "暂无 chunk。请先重建索引，或换一个过滤词。";
    return;
  }
  target.className = "library-chunks";
  target.innerHTML = chunks
    .map((chunk) => {
      const id = chunk.chunk_id || "chunk";
      const page = chunk.page ? `page=${chunk.page}` : "page=unknown";
      const parser = formatParser(chunk.metadata || {});
      const text = escapeHtml(chunk.content || "").slice(0, 520);
      return `<div class="library-chunk"><strong>${escapeHtml(chunk.source)}</strong> · ${escapeHtml(
        id
      )} · ${escapeHtml(page)} · parser=${escapeHtml(parser)}<br>${text}</div>`;
    })
    .join("");
  addLog(`已加载 ${chunks.length}/${total} 个 chunk。`);
}

async function loadChunks(filename = state.selectedDocument) {
  const query = $("#chunkQuery").value.trim();
  const base = filename
    ? `/documents/${encodeURIComponent(filename)}/chunks`
    : "/documents/chunks";
  const params = new URLSearchParams({ limit: "80" });
  if (query) params.set("query", query);
  try {
    const data = await requestJson(`${base}?${params.toString()}`);
    renderLibraryChunks(data.chunks || [], data.total || 0);
  } catch (error) {
    $("#libraryChunks").className = "library-chunks empty";
    $("#libraryChunks").textContent = `读取 chunk 失败：${error.message}`;
  }
}

function parseSseBlock(block) {
  const eventLine = block
    .split("\n")
    .find((line) => line.startsWith("event:"));
  const dataLines = block
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim());
  return {
    event: eventLine ? eventLine.slice(6).trim() : "message",
    data: dataLines.length ? JSON.parse(dataLines.join("\n")) : {},
  };
}

async function runStreamingRag(question, topK) {
  const response = await fetch("/chat/rag/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });
  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${response.status}`);
  }

  const target = $("#answer");
  target.dataset.raw = "";
  target.innerHTML = "正在生成...";

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary).trim();
      buffer = buffer.slice(boundary + 2);
      if (block) {
        const message = parseSseBlock(block);
        if (message.event === "meta") {
          renderSources(message.data.sources || []);
          renderChunks(message.data.related_chunks || []);
        } else if (message.event === "delta") {
          appendAnswer(message.data.text || "");
        } else if (message.event === "error") {
          throw new Error(message.data.message || "流式生成失败");
        }
      }
      boundary = buffer.indexOf("\n\n");
    }

    if (done) {
      break;
    }
  }
}

async function runQuery(event) {
  event.preventDefault();
  const question = $("#questionInput").value.trim();
  const topK = Number($("#topK").value || 4);
  if (!question) {
    addLog("请输入问题。");
    return;
  }

  const done = setBusy($(".run"), "生成中");
  const started = performance.now();
  renderAnswer("正在检索资料并生成回答...");
  renderSources([]);
  renderChunks([]);

  try {
    let data;
    if (state.mode === "search") {
      data = await requestJson("/knowledge/search", {
        method: "POST",
        body: JSON.stringify({ query: question, top_k: topK }),
      });
      const answer = data.results
        .map((item, index) => `${index + 1}. ${item.source}\n${item.content}`)
        .join("\n\n");
      renderAnswer(answer || "没有检索到相关片段。");
      renderSources(
        data.results.map((item) => ({
          source: item.source,
          page: item.page,
          chunk_id: item.metadata?.chunk_id,
        }))
      );
      renderChunks(data.results);
      $("#resultMode").textContent = "knowledge.search";
    } else if (state.mode === "rag" && $("#streamToggle").checked) {
      await runStreamingRag(question, topK);
      $("#resultMode").textContent = "chat.rag.stream";
    } else {
      const endpoint = state.mode === "rag" ? "/chat/rag" : "/chat/agent";
      data = await requestJson(endpoint, {
        method: "POST",
        body: JSON.stringify({ question, top_k: topK }),
      });
      renderAnswer(data.answer);
      renderSources(data.sources || []);
      renderChunks(data.related_chunks || []);
      $("#resultMode").textContent = state.mode === "rag" ? "chat.rag" : `agent.${data.intent}`;
    }
    const seconds = (performance.now() - started) / 1000;
    $("#latency").textContent = `${seconds.toFixed(2)}s`;
    addLog(`完成：${question}`);
  } catch (error) {
    renderAnswer(`请求失败：${error.message}`);
    addLog(`请求失败：${error.message}`);
  } finally {
    done();
  }
}

async function runEval() {
  const limit = Number($("#evalLimit").value || 5);
  const done = setBusy($("#evalBtn"), "评测中");
  try {
    const data = await requestJson("/eval/run", {
      method: "POST",
      body: JSON.stringify({ limit }),
    });
    renderAnswer(
      [
        `评测样本：${data.total}`,
        `来源命中率：${(data.source_hit_rate * 100).toFixed(2)}%`,
        `关键词命中率：${(data.keyword_hit_rate * 100).toFixed(2)}%`,
        `Recall@K：${(data.retrieval_recall_at_k * 100).toFixed(2)}%`,
        `MRR：${data.mean_reciprocal_rank.toFixed(3)}`,
        `平均耗时：${data.avg_latency.toFixed(2)}s`,
        `失败样例：${data.failed_cases.length}`,
      ].join("\n")
    );
    $("#resultMode").textContent = "eval.run";
    $("#latency").textContent = "done";
    renderSources([]);
    renderChunks([]);
    addLog(`评测完成：${data.total} 条。`);
  } catch (error) {
    addLog(`评测失败：${error.message}`);
  } finally {
    done();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  checkHealth();

  $("#refreshHealth").addEventListener("click", checkHealth);
  $("#uploadBtn").addEventListener("click", uploadDocument);
  $("#buildBtn").addEventListener("click", buildKnowledge);
  $("#evalBtn").addEventListener("click", runEval);
  $("#refreshDocsBtn").addEventListener("click", loadDocuments);
  $("#allChunksBtn").addEventListener("click", () => {
    state.selectedDocument = null;
    $("#docFilename").value = "";
    $("#docEditor").value = "";
    $("#docEditor").disabled = false;
    loadDocuments();
    loadChunks(null);
  });
  $("#newDocBtn").addEventListener("click", createDocumentFromEditor);
  $("#saveDocBtn").addEventListener("click", saveSelectedDocument);
  $("#deleteDocBtn").addEventListener("click", deleteSelectedDocument);
  $("#filterChunksBtn").addEventListener("click", () => loadChunks(state.selectedDocument));
  $("#queryForm").addEventListener("submit", runQuery);
  $("#clearLog").addEventListener("click", () => {
    $("#log").innerHTML = "";
  });

  $("#fileInput").addEventListener("change", (event) => {
    const file = event.target.files[0];
    $("#fileLabel").textContent = file ? file.name : "选择文档";
  });

  document.querySelectorAll(".mode").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".mode").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.mode = button.dataset.mode;
      addLog(`切换模式：${state.mode}`);
    });
  });

  loadDocuments();
  loadChunks(null);
});
