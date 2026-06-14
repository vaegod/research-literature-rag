from app.chains import rag_chain
from app.models.schemas import SearchResult


def test_generate_rag_answer_uses_context(monkeypatch) -> None:
    def fake_complete_chat(system_prompt: str, user_prompt: str, temperature=None) -> str:
        assert "source=lora_finetuning_notes.md" in user_prompt
        assert "LoRA 为什么能减少训练参数" in user_prompt
        assert "不要只复述原文" in user_prompt
        assert "解释方法机制" in user_prompt
        assert "这是闭卷 RAG" in system_prompt
        assert "不要写参考资料中没有明确出现的公式" in user_prompt
        assert temperature == rag_chain.ANSWER_TEMPERATURE
        return "LoRA 通过低秩矩阵减少训练参数。引用来源：lora_finetuning_notes.md"

    monkeypatch.setattr(rag_chain, "complete_chat", fake_complete_chat)
    chunks = [
        SearchResult(
            content="LoRA 额外学习两个低秩矩阵。",
            source="lora_finetuning_notes.md",
            page=1,
            score=0.1,
            metadata={"chunk_id": "lora_chunk_0001"},
        )
    ]

    answer = rag_chain.generate_rag_answer("LoRA 为什么能减少训练参数？", chunks)

    assert "低秩矩阵" in answer
    assert "引用来源" in answer
