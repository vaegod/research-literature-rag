from __future__ import annotations

import json
import re

from app.chains.clients import complete_chat
from app.chains.general_chain import generate_general_answer
from app.config import get_settings
from app.graph.state import AgentState
from app.tools.experiment_tool import run_experiment_query
from app.tools.literature_tool import run_literature_qa
from app.tools.note_tool import run_note_generation
from app.tools.paper_compare_tool import run_paper_compare

ALLOWED_INTENTS = {
    "literature_qa",
    "paper_compare",
    "experiment_query",
    "note_generation",
    "general_chat",
}

ROUTER_SYSTEM_PROMPT = """你是科研问答系统的意图路由器。
只输出 JSON，不要输出解释性文本。
可选 intent 只能是：
literature_qa, paper_compare, experiment_query, note_generation, general_chat。
字段格式：
{"intent":"literature_qa","confidence":0.0,"reason":"简短原因"}"""


def classify_intent_rule(question: str) -> str:
    return _classify_intent_rule_with_meta(question)["intent"]


def classify_intent_with_metadata(question: str) -> dict:
    settings = get_settings()
    rule_result = _classify_intent_rule_with_meta(question)
    mode = settings.agent_router_mode
    if mode == "rule" or rule_result["router_confidence"] >= 0.95 or not settings.has_api_key:
        return {**rule_result, "router": "rule"}
    if mode not in {"hybrid", "llm"}:
        return {**rule_result, "router": "rule"}

    try:
        llm_result = _classify_intent_llm(question)
    except Exception:
        return {**rule_result, "router": "rule_fallback"}

    if llm_result["router_confidence"] < 0.45 and mode == "hybrid":
        return {**rule_result, "router": "rule_fallback"}
    return {**llm_result, "router": "llm"}


def _classify_intent_rule_with_meta(question: str) -> dict:
    text = question.lower()
    if re.search(r"exp-\d+", text) or "实验记录" in question or (
        "查询" in question and ("实验" in question or "效果" in question)
    ):
        return {
            "intent": "experiment_query",
            "router_confidence": 0.98,
            "router_reason": "命中实验编号或明确实验记录查询",
        }
    if any(keyword in question for keyword in ["阅读笔记", "生成笔记", "论文笔记", "总结这篇"]):
        return {
            "intent": "note_generation",
            "router_confidence": 0.94,
            "router_reason": "命中阅读笔记生成关键词",
        }
    if any(keyword in question for keyword in ["对比", "比较", "区别", "差异", "优缺点"]):
        return {
            "intent": "paper_compare",
            "router_confidence": 0.9,
            "router_reason": "命中对比分析关键词",
        }
    if any(keyword in question for keyword in ["你好", "你是谁", "帮助", "怎么使用"]):
        return {
            "intent": "general_chat",
            "router_confidence": 0.96,
            "router_reason": "命中通用问答关键词",
        }
    return {
        "intent": "literature_qa",
        "router_confidence": 0.6,
        "router_reason": "默认进入文献问答",
    }


def _classify_intent_llm(question: str) -> dict:
    raw = complete_chat(
        ROUTER_SYSTEM_PROMPT,
        f"用户问题：{question}",
        temperature=0,
    )
    payload = _extract_json_object(raw)
    intent = payload.get("intent", "literature_qa")
    if intent not in ALLOWED_INTENTS:
        intent = "literature_qa"
    confidence = payload.get("confidence", 0.6)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.6
    confidence = max(0.0, min(confidence, 1.0))
    return {
        "intent": intent,
        "router_confidence": confidence,
        "router_reason": str(payload.get("reason", "LLM router")),
    }


def _extract_json_object(text: str) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("Router did not return JSON.")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("Router JSON must be an object.")
    return payload


def classify_intent(state: AgentState) -> AgentState:
    if state.get("intent") and state.get("router"):
        return {}
    return classify_intent_with_metadata(state["question"])


def literature_qa_node(state: AgentState) -> AgentState:
    result = run_literature_qa(state["question"], state.get("top_k"))
    return {**result}


def paper_compare_node(state: AgentState) -> AgentState:
    result = run_paper_compare(state["question"], state.get("top_k"))
    return {**result}


def experiment_query_node(state: AgentState) -> AgentState:
    result = run_experiment_query(state["question"])
    return {
        "answer": result["answer"],
        "sources": [],
        "related_chunks": [],
        "tool_result": result,
    }


def note_generation_node(state: AgentState) -> AgentState:
    result = run_note_generation(state["question"], state.get("top_k"))
    return {**result}


def general_chat_node(state: AgentState) -> AgentState:
    try:
        answer = generate_general_answer(state["question"])
    except RuntimeError:
        answer = "你好，我是科研文献智能问答助手。配置 API Key 后可以进行文献问答、论文对比、实验查询和阅读笔记生成。"
    return {"answer": answer, "sources": [], "related_chunks": [], "tool_result": {"mode": "general_chat"}}


def route_by_intent(state: AgentState) -> str:
    return state.get("intent", "literature_qa")
