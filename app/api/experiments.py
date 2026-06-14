from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import ExperimentSearchRequest, ExperimentSearchResponse
from app.tools.experiment_tool import search_experiments

router = APIRouter()


@router.post("/search", response_model=ExperimentSearchResponse)
def search_experiment_records(req: ExperimentSearchRequest) -> ExperimentSearchResponse:
    results = search_experiments(req.query)
    return ExperimentSearchResponse(query=req.query, total=len(results), results=results)
