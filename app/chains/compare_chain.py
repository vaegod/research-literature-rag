from __future__ import annotations

from app.chains.clients import complete_chat
from app.chains.prompts import COMPARE_SYSTEM_PROMPT
from app.chains.rag_chain import ANSWER_TEMPERATURE, ensure_reference_block, format_context
from app.models.schemas import SearchResult


def generate_compare_answer(question: str, chunks: list[SearchResult]) -> str:
    if not chunks:
        return "当前知识库没有检索到可用于对比的文献片段。"

    user_prompt = f"""对比问题：
{question}

参考资料：
{format_context(chunks)}

请完成结构化对比分析。不要逐条复述参考资料，要抽象出对比维度和使用建议。"""
    return ensure_reference_block(
        complete_chat(COMPARE_SYSTEM_PROMPT, user_prompt, temperature=ANSWER_TEMPERATURE),
        chunks,
    )
