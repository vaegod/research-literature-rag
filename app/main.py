from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import chat, documents, experiments, knowledge
from app.api import eval as eval_api
from app.config import PROJECT_ROOT, ensure_data_directories, get_settings
from app.models.schemas import HealthResponse
from app.services.document_service import get_knowledge_status

ensure_data_directories()
settings = get_settings()

app = FastAPI(
    title="Research Literature RAG Agent API",
    description="科研文献智能问答与实验分析助手",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "app" / "static"), name="static")


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    knowledge_status = get_knowledge_status(settings)
    return HealthResponse(
        status="ok",
        service="research-literature-rag-agent",
        version=settings.app_version,
        has_api_key=settings.has_api_key,
        **knowledge_status,
    )


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "app" / "static" / "index.html")


app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
app.include_router(eval_api.router, prefix="/eval", tags=["eval"])
