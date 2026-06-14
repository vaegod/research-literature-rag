from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import EvalRunRequest, EvalRunResponse
from app.services.eval_service import run_eval

router = APIRouter()


@router.post("/run", response_model=EvalRunResponse)
def run_rag_eval(req: EvalRunRequest) -> EvalRunResponse:
    try:
        return run_eval(limit=req.limit)
    except (RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
