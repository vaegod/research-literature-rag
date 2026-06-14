from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.chains.rag_chain import generate_rag_answer_stream
from app.errors import DependencyMissingError, ModelProviderError
from app.models.schemas import AgentResponse, ChatRequest, RAGResponse
from app.services.agent_service import ask_agent
from app.services.rag_service import ask_rag
from app.services.rag_service import search as search_rag
from app.utils.response import collect_sources

router = APIRouter()


@router.post("/rag", response_model=RAGResponse)
def rag_chat(req: ChatRequest) -> RAGResponse:
    try:
        return ask_rag(req.question, req.top_k)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ModelProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DependencyMissingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rag/stream")
def rag_chat_stream(req: ChatRequest) -> StreamingResponse:
    try:
        chunks = search_rag(req.question, req.top_k)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ModelProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DependencyMissingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(
        _rag_sse_events(req.question, chunks),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/agent", response_model=AgentResponse)
def agent_chat(req: ChatRequest) -> AgentResponse:
    try:
        return ask_agent(req.question, req.top_k)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ModelProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DependencyMissingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _rag_sse_events(question: str, chunks: list) -> Iterator[str]:
    yield _sse(
        "meta",
        {
            "sources": [source.model_dump() for source in collect_sources(chunks)],
            "related_chunks": [chunk.model_dump() for chunk in chunks],
        },
    )
    try:
        for delta in generate_rag_answer_stream(question, chunks):
            yield _sse("delta", {"text": delta})
    except (ModelProviderError, RuntimeError) as exc:
        yield _sse("error", {"message": str(exc)})
        return
    yield _sse("done", {})


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
