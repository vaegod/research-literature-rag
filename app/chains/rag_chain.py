from __future__ import annotations

from collections.abc import Iterator

from app.chains.clients import complete_chat, stream_chat
from app.chains.prompts import RAG_SYSTEM_PROMPT
from app.models.schemas import SearchResult
from app.retriever.retrieval import infer_retrieval_intent

ANSWER_TEMPERATURE = 0.25


def format_context(chunks: list[SearchResult]) -> str:
    lines: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_id = chunk.metadata.get("chunk_id", f"chunk_{index}")
        page = chunk.page if chunk.page is not None else "unknown"
        lines.append(
            "\n".join(
                [
                    f"[S{index}] source={chunk.source}; page={page}; chunk_id={chunk_id}",
                    chunk.content,
                ]
            )
        )
    return "\n\n---\n\n".join(lines)


def generate_rag_answer(question: str, chunks: list[SearchResult]) -> str:
    if not chunks:
        return "当前知识库没有检索到足够相关的文献片段，暂时无法基于资料回答。"

    user_prompt = build_rag_user_prompt(question, chunks)
    return ensure_reference_block(
        complete_chat(RAG_SYSTEM_PROMPT, user_prompt, temperature=ANSWER_TEMPERATURE),
        chunks,
    )


def generate_rag_answer_stream(question: str, chunks: list[SearchResult]) -> Iterator[str]:
    if not chunks:
        yield "当前知识库没有检索到足够相关的文献片段，暂时无法基于资料回答。"
        return

    user_prompt = build_rag_user_prompt(question, chunks)
    streamed: list[str] = []
    for token in stream_chat(RAG_SYSTEM_PROMPT, user_prompt, temperature=ANSWER_TEMPERATURE):
        streamed.append(token)
        yield token

    raw_answer = "".join(streamed)
    final_answer = ensure_reference_block(raw_answer, chunks)
    if final_answer != raw_answer:
        yield final_answer[len(raw_answer) :]


def build_rag_user_prompt(question: str, chunks: list[SearchResult]) -> str:
    intent = infer_retrieval_intent(question)
    return f"""用户问题：
{question}

问题类型：
{intent}

回答任务：
{answer_task_for_intent(intent)}

参考资料：
{format_context(chunks)}

请把参考资料当作证据进行综合回答，不要只复述原文。不要写参考资料中没有明确出现的公式、矩阵维度、数字例子或外部常识。关键结论后尽量标注 [S1] 这类来源编号。"""


def answer_task_for_intent(intent: str) -> str:
    tasks = {
        "contribution": "提炼论文或资料的核心贡献：说明它解决了什么问题、提出了什么新做法、价值在哪里，以及这些判断分别由哪些证据支持。",
        "method": "解释方法机制：按流程拆解关键步骤，说明每一步的作用、输入输出和为什么这样设计。",
        "experiment": "分析实验信息：总结实验设置、数据或指标、主要现象，并解释这些结果能支持什么结论。",
        "limitation": "归纳局限与风险：区分资料明确提到的不足和根据资料可谨慎推出的约束，不要扩大结论。",
        "summary": "做结构化总结：先给整体结论，再按背景、方法、实验/证据、意义分层整理。",
        "general": "围绕用户问题给出直接结论，并综合多个片段解释原因、影响和使用场景。",
    }
    return tasks.get(intent, tasks["general"])


def ensure_reference_block(answer: str, chunks: list[SearchResult]) -> str:
    answer = answer.strip() or "当前资料不足以生成回答。"
    references = _format_references(chunks)
    if not references:
        return answer
    if "引用来源" in answer and any(f"[S{index}]" in answer for index in range(1, len(chunks) + 1)):
        return answer
    return f"{answer}\n\n引用来源：\n" + "\n".join(references)


def _format_references(chunks: list[SearchResult]) -> list[str]:
    references: list[str] = []
    seen: set[tuple[str, int | None, str | None]] = set()
    for index, chunk in enumerate(chunks, start=1):
        chunk_id = chunk.metadata.get("chunk_id") or chunk.metadata.get("doc_id")
        key = (chunk.source, chunk.page, str(chunk_id) if chunk_id is not None else None)
        if key in seen:
            continue
        seen.add(key)
        page = f"page={chunk.page}" if chunk.page is not None else "page=unknown"
        chunk_part = f"; chunk_id={chunk_id}" if chunk_id else ""
        references.append(f"[S{index}] {chunk.source}; {page}{chunk_part}")
    return references
