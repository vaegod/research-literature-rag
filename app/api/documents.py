from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.models.schemas import (
    DocumentChunksResponse,
    DocumentContentResponse,
    DocumentCreateRequest,
    DocumentListResponse,
    DocumentMutationResponse,
    DocumentUpdateRequest,
    UploadDocumentResponse,
)
from app.services.document_service import (
    create_text_document,
    delete_document,
    list_document_chunks,
    list_documents,
    read_document,
    save_document,
    update_document,
)

router = APIRouter()


@router.post("/upload", response_model=UploadDocumentResponse)
async def upload_document(file: Annotated[UploadFile, File(...)]) -> UploadDocumentResponse:
    try:
        return await save_document(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=DocumentListResponse)
def get_documents() -> DocumentListResponse:
    return list_documents()


@router.post("", response_model=DocumentMutationResponse)
def create_document(req: DocumentCreateRequest) -> DocumentMutationResponse:
    try:
        return create_text_document(req.filename, req.content)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/chunks", response_model=DocumentChunksResponse)
def get_all_chunks(
    query: str | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=500),
) -> DocumentChunksResponse:
    return list_document_chunks(query=query, limit=limit)


@router.get("/{filename}/chunks", response_model=DocumentChunksResponse)
def get_document_chunks(
    filename: str,
    query: str | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=500),
) -> DocumentChunksResponse:
    return list_document_chunks(filename=filename, query=query, limit=limit)


@router.get("/{filename}", response_model=DocumentContentResponse)
def get_document(filename: str) -> DocumentContentResponse:
    try:
        return read_document(filename)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{filename}", response_model=DocumentMutationResponse)
def put_document(filename: str, req: DocumentUpdateRequest) -> DocumentMutationResponse:
    try:
        return update_document(filename, req.content)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{filename}", response_model=DocumentMutationResponse)
def remove_document(filename: str) -> DocumentMutationResponse:
    try:
        return delete_document(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
