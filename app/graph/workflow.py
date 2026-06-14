from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.graph.nodes import (
    classify_intent,
    classify_intent_rule,
    classify_intent_with_metadata,
    experiment_query_node,
    general_chat_node,
    literature_qa_node,
    note_generation_node,
    paper_compare_node,
    route_by_intent,
)
from app.graph.state import AgentState


@lru_cache(maxsize=1)
def build_workflow():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("literature_qa", literature_qa_node)
    graph.add_node("paper_compare", paper_compare_node)
    graph.add_node("experiment_query", experiment_query_node)
    graph.add_node("note_generation", note_generation_node)
    graph.add_node("general_chat", general_chat_node)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "literature_qa": "literature_qa",
            "paper_compare": "paper_compare",
            "experiment_query": "experiment_query",
            "note_generation": "note_generation",
            "general_chat": "general_chat",
        },
    )
    for node_name in (
        "literature_qa",
        "paper_compare",
        "experiment_query",
        "note_generation",
        "general_chat",
    ):
        graph.add_edge(node_name, END)
    return graph.compile()


def run_agent(question: str, top_k: int | None = None) -> AgentState:
    settings = get_settings()
    initial_state: AgentState = {
        "question": question,
        "top_k": top_k or settings.default_top_k,
        **classify_intent_with_metadata(question),
    }
    try:
        return build_workflow().invoke(initial_state)
    except ImportError:
        return _run_agent_without_langgraph(initial_state)


def _run_agent_without_langgraph(state: AgentState) -> AgentState:
    intent = state.get("intent") or classify_intent_rule(state["question"])
    handlers = {
        "literature_qa": literature_qa_node,
        "paper_compare": paper_compare_node,
        "experiment_query": experiment_query_node,
        "note_generation": note_generation_node,
        "general_chat": general_chat_node,
    }
    result = handlers.get(intent, literature_qa_node)(state)
    return {**state, **result, "intent": intent}
