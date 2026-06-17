from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    has_api_key: bool = False
    pdf_parser: str = "pypdf"
    mineru_enabled: bool = False
    mineru_has_token: bool = False
    mineru_model_version: str = ""
    index_exists: bool = False
    raw_doc_count: int = 0
    chunk_count: int = 0


class BuildKnowledgeRequest(BaseModel):
    force_rebuild: bool = Field(default=True, description="是否重新构建 FAISS 索引")


class BuildKnowledgeResponse(BaseModel):
    status: str
    loaded_documents: int
    generated_chunks: int
    vector_store_path: str


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class SearchResult(BaseModel):
    content: str
    source: str
    page: int | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchResponse(BaseModel):
    query: str
    top_k: int
    results: list[SearchResult]


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class Source(BaseModel):
    source: str
    page: int | None = None
    chunk_id: str | None = None


class RAGResponse(BaseModel):
    answer: str
    sources: list[Source]
    related_chunks: list[SearchResult]


class AgentResponse(BaseModel):
    answer: str
    intent: str
    sources: list[Source] = Field(default_factory=list)
    related_chunks: list[SearchResult] = Field(default_factory=list)
    tool_result: dict[str, Any] = Field(default_factory=dict)


class ExperimentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)


class ExperimentSearchResponse(BaseModel):
    query: str
    total: int
    results: list[dict[str, Any]]


class EvalRunRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1)


class EvalCaseResult(BaseModel):
    id: str
    question: str
    intent: str
    source_hit: bool
    keyword_hit: bool
    retrieval_hit: bool | None = None
    reciprocal_rank: float | None = None
    latency: float
    answer_preview: str
    expected_chunk_ids: list[str] = Field(default_factory=list)
    observed_chunk_ids: list[str] = Field(default_factory=list)


class EvalRunResponse(BaseModel):
    total: int
    source_hit_rate: float
    keyword_hit_rate: float
    retrieval_recall_at_k: float = 0.0
    mean_reciprocal_rank: float = 0.0
    avg_latency: float
    failed_cases: list[EvalCaseResult]


class UploadDocumentResponse(BaseModel):
    filename: str
    saved_path: str
    size: int
    index_status: str = "stale"
    message: str = "文档已上传，索引已过期；请调用 /knowledge/build 同步向量知识库。"


class DocumentSummary(BaseModel):
    filename: str
    file_type: str
    size: int
    modified_time: str
    chunk_count: int = 0
    editable: bool


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentSummary]


class DocumentContentResponse(BaseModel):
    filename: str
    content: str
    editable: bool
    message: str = ""


class DocumentCreateRequest(BaseModel):
    filename: str = Field(..., min_length=1)
    content: str = ""


class DocumentUpdateRequest(BaseModel):
    content: str


class DocumentMutationResponse(BaseModel):
    filename: str
    status: str
    message: str
    index_status: str = "stale"


class KnowledgeChunk(BaseModel):
    content: str
    source: str
    page: int | None = None
    chunk_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentChunksResponse(BaseModel):
    filename: str | None = None
    total: int
    chunks: list[KnowledgeChunk]
