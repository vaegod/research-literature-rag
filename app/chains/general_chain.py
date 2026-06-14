from __future__ import annotations

from app.chains.clients import complete_chat
from app.chains.prompts import GENERAL_SYSTEM_PROMPT


def generate_general_answer(question: str) -> str:
    user_prompt = f"用户问题：{question}"
    return complete_chat(GENERAL_SYSTEM_PROMPT, user_prompt)
