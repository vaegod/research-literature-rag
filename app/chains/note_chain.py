from __future__ import annotations

from app.chains.clients import complete_chat
from app.chains.prompts import NOTE_SYSTEM_PROMPT
from app.chains.rag_chain import ANSWER_TEMPERATURE, ensure_reference_block, format_context
from app.models.schemas import SearchResult


def generate_note_answer(question: str, chunks: list[SearchResult]) -> str:
    if not chunks:
        return "当前知识库没有检索到可生成阅读笔记的文献片段。"

    user_prompt = f"""阅读笔记需求：
{question}

参考资料：
{format_context(chunks)}

请生成结构化阅读笔记。不要按 chunk 顺序机械摘要，要整合为研究者笔记。"""
    return ensure_reference_block(
        complete_chat(NOTE_SYSTEM_PROMPT, user_prompt, temperature=ANSWER_TEMPERATURE),
        chunks,
    )
