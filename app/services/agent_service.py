from __future__ import annotations

from app.graph.workflow import run_agent
from app.models.schemas import AgentResponse


def ask_agent(question: str, top_k: int | None = None) -> AgentResponse:
    state = run_agent(question, top_k)
    tool_result = dict(state.get("tool_result", {}) or {})
    for key in ("router", "router_confidence", "router_reason"):
        if key in state:
            tool_result.setdefault(key, state[key])
    return AgentResponse(
        answer=state.get("answer", ""),
        intent=state.get("intent", "literature_qa"),
        sources=state.get("sources", []),
        related_chunks=state.get("related_chunks", []),
        tool_result=tool_result,
    )
