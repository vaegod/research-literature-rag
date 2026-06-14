from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.errors import DependencyMissingError, ModelProviderError
from app.models.schemas import (
    BuildKnowledgeRequest,
    BuildKnowledgeResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.document_service import build_knowledge_base
from app.services.rag_service import search

router = APIRouter()


@router.post("/build", response_model=BuildKnowledgeResponse)
def build_knowledge(req: BuildKnowledgeRequest) -> BuildKnowledgeResponse:
    try:
        return build_knowledge_base(force_rebuild=req.force_rebuild)
    except ModelProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DependencyMissingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(req: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
    settings = get_settings()
    top_k = req.top_k or settings.default_top_k
    try:
        results = search(req.query, top_k)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ModelProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DependencyMissingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return KnowledgeSearchResponse(query=req.query, top_k=top_k, results=results)
