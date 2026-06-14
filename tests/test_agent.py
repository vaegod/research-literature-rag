from app.graph.nodes import classify_intent_rule


def test_intent_classification() -> None:
    assert classify_intent_rule("知识蒸馏的核心思想是什么？") == "literature_qa"
    assert classify_intent_rule("对比 LoRA 和知识蒸馏") == "paper_compare"
    assert classify_intent_rule("查询 EXP-002 的实验结果") == "experiment_query"
    assert classify_intent_rule("帮我生成 RAG 论文的阅读笔记") == "note_generation"
    assert classify_intent_rule("你好，你是谁？") == "general_chat"
    assert classify_intent_rule("accuracy 适合什么场景？") == "literature_qa"
    assert classify_intent_rule("这篇论文做了哪些实验，使用了哪些指标？") == "literature_qa"
