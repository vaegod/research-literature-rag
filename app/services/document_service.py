from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile

from app.config import Settings, ensure_data_directories, get_settings
from app.models.schemas import (
    BuildKnowledgeResponse,
    DocumentChunksResponse,
    DocumentContentResponse,
    DocumentListResponse,
    DocumentMutationResponse,
    DocumentSummary,
    KnowledgeChunk,
    UploadDocumentResponse,
)
from app.retriever.loaders import load_documents
from app.retriever.splitters import split_documents
from app.retriever.vector_store import build_vector_store
from app.utils.file_utils import safe_filename, save_upload_file, validate_supported_file

EDITABLE_EXTENSIONS = {".md", ".markdown", ".txt"}


async def save_document(upload_file: UploadFile) -> UploadDocumentResponse:
    settings = get_settings()
    ensure_data_directories(settings)
    saved_path, size = await save_upload_file(
        upload_file,
        settings.raw_docs_path,
        max_size_bytes=settings.max_upload_size_bytes,
    )
    return UploadDocumentResponse(
        filename=saved_path.name,
        saved_path=str(saved_path),
        size=size,
    )


def list_documents(settings: Settings | None = None) -> DocumentListResponse:
    settings = settings or get_settings()
    ensure_data_directories(settings)
    chunk_counts = _chunk_counts(settings)
    documents: list[DocumentSummary] = []

    for path in sorted(settings.raw_docs_path.iterdir()):
        if not path.is_file():
            continue
        try:
            validate_supported_file(path.name)
        except ValueError:
            continue
        stat = path.stat()
        documents.append(
            DocumentSummary(
                filename=path.name,
                file_type=path.suffix.lower().lstrip("."),
                size=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                chunk_count=chunk_counts.get(path.name, 0),
                editable=path.suffix.lower() in EDITABLE_EXTENSIONS,
            )
        )

    return DocumentListResponse(total=len(documents), documents=documents)


def create_text_document(
    filename: str,
    content: str,
    settings: Settings | None = None,
) -> DocumentMutationResponse:
    settings = settings or get_settings()
    ensure_data_directories(settings)
    target = _resolve_raw_doc(filename, must_exist=False, settings=settings)
    if target.suffix.lower() not in EDITABLE_EXTENSIONS:
        raise ValueError("Only Markdown and TXT documents can be created from the editor.")
    if not content.strip():
        raise ValueError("Document content cannot be empty.")
    if target.exists():
        raise FileExistsError(f"Document already exists: {target.name}")

    target.write_text(content, encoding="utf-8")
    return DocumentMutationResponse(
        filename=target.name,
        status="created",
        message="文档已创建，索引已过期；请调用 /knowledge/build 同步向量知识库。",
    )


def read_document(
    filename: str,
    settings: Settings | None = None,
) -> DocumentContentResponse:
    settings = settings or get_settings()
    path = _resolve_raw_doc(filename, must_exist=True, settings=settings)
    editable = path.suffix.lower() in EDITABLE_EXTENSIONS
    if not editable:
        return DocumentContentResponse(
            filename=path.name,
            content="",
            editable=False,
            message="PDF 文件暂不支持在前端直接编辑，请上传替换后重建索引。",
        )

    return DocumentContentResponse(
        filename=path.name,
        content=path.read_text(encoding="utf-8", errors="ignore"),
        editable=True,
    )


def update_document(
    filename: str,
    content: str,
    settings: Settings | None = None,
) -> DocumentMutationResponse:
    settings = settings or get_settings()
    path = _resolve_raw_doc(filename, must_exist=True, settings=settings)
    if path.suffix.lower() not in EDITABLE_EXTENSIONS:
        raise ValueError("Only Markdown and TXT documents can be edited in the browser.")
    if not content.strip():
        raise ValueError("Document content cannot be empty.")

    path.write_text(content, encoding="utf-8")
    return DocumentMutationResponse(
        filename=path.name,
        status="updated",
        message="文档已保存，索引已过期；请调用 /knowledge/build 同步向量知识库。",
    )


def delete_document(
    filename: str,
    settings: Settings | None = None,
) -> DocumentMutationResponse:
    settings = settings or get_settings()
    path = _resolve_raw_doc(filename, must_exist=True, settings=settings)
    path.unlink()
    return DocumentMutationResponse(
        filename=path.name,
        status="deleted",
        message="文档已删除，索引已过期；请调用 /knowledge/build 同步向量知识库。",
    )


def list_document_chunks(
    filename: str | None = None,
    query: str | None = None,
    limit: int = 80,
    settings: Settings | None = None,
) -> DocumentChunksResponse:
    settings = settings or get_settings()
    chunks = _read_processed_chunks(settings)
    if filename:
        normalized = _resolve_raw_doc(filename, must_exist=False, settings=settings).name
        chunks = [chunk for chunk in chunks if chunk.source == normalized]
    if query:
        lowered = query.lower()
        chunks = [
            chunk
            for chunk in chunks
            if lowered in chunk.content.lower() or lowered in chunk.source.lower()
        ]
    limited = chunks[: max(limit, 1)]
    return DocumentChunksResponse(filename=filename, total=len(chunks), chunks=limited)


def build_knowledge_base(
    force_rebuild: bool = True,
    settings: Settings | None = None,
) -> BuildKnowledgeResponse:
    settings = settings or get_settings()
    ensure_data_directories(settings)

    index_file = settings.vector_store_path / "index.faiss"
    if index_file.exists() and not force_rebuild:
        return BuildKnowledgeResponse(
            status="skipped",
            loaded_documents=0,
            generated_chunks=0,
            vector_store_path=str(settings.vector_store_path),
        )

    documents = load_documents(settings.raw_docs_path)
    chunks = split_documents(documents, settings.chunk_size, settings.chunk_overlap)
    _write_processed_chunks(chunks, settings.processed_docs_path / "chunks.jsonl")
    build_vector_store(chunks, settings)
    return BuildKnowledgeResponse(
        status="ok",
        loaded_documents=len(documents),
        generated_chunks=len(chunks),
        vector_store_path=str(settings.vector_store_path),
    )


def get_knowledge_status(settings: Settings | None = None) -> dict[str, int | bool]:
    settings = settings or get_settings()
    ensure_data_directories(settings)
    raw_doc_count = 0
    for path in settings.raw_docs_path.iterdir():
        if not path.is_file():
            continue
        try:
            validate_supported_file(path.name)
        except ValueError:
            continue
        raw_doc_count += 1

    index_exists = (
        (settings.vector_store_path / "index.faiss").exists()
        and (settings.vector_store_path / "index.pkl").exists()
    )
    return {
        "index_exists": index_exists,
        "raw_doc_count": raw_doc_count,
        "chunk_count": len(_read_processed_chunks(settings)),
    }


def _write_processed_chunks(chunks: list, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            payload = {
                "text": chunk.page_content,
                "metadata": chunk.metadata,
            }
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _resolve_raw_doc(filename: str, must_exist: bool, settings: Settings) -> Path:
    normalized = safe_filename(filename)
    validate_supported_file(normalized)
    path = settings.raw_docs_path / normalized
    try:
        path.resolve().relative_to(settings.raw_docs_path.resolve())
    except ValueError as exc:
        raise ValueError("Invalid document path.") from exc
    if must_exist and not path.exists():
        raise FileNotFoundError(f"Document not found: {normalized}")
    return path


def _chunk_counts(settings: Settings) -> dict[str, int]:
    counts: dict[str, int] = {}
    for chunk in _read_processed_chunks(settings):
        counts[chunk.source] = counts.get(chunk.source, 0) + 1
    return counts


def _read_processed_chunks(settings: Settings) -> list[KnowledgeChunk]:
    path = settings.processed_docs_path / "chunks.jsonl"
    if not path.exists():
        return []

    chunks: list[KnowledgeChunk] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            payload = json.loads(line)
            metadata = payload.get("metadata", {})
            chunks.append(
                KnowledgeChunk(
                    content=payload.get("text", ""),
                    source=str(metadata.get("source", "")),
                    page=metadata.get("page"),
                    chunk_id=metadata.get("chunk_id"),
                    metadata=metadata,
                )
            )
    return chunks
