# 知识库管理接口

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, File, Path, Query, UploadFile
from fastapi.responses import FileResponse

from app.exceptions import AppException
from app.schemas.knowledge.document_schema import BaseCreate, BaseInfo, ChunkInfo, DocumentInfo, SearchHit
from app.schemas.result import Result
from app.services.knowledge.document_service import (
    remove_base,
    remove_document,
    save_document,
    schedule_document,
)
from harness.rag.document.repository import (
    create_base,
    get_base,
    get_document,
    list_bases,
    list_chunks,
    list_documents,
    set_document_status,
)
from harness.rag.retrieval.pipeline import search_knowledge
from harness.rag.store import document_path


router = APIRouter(tags=["知识库"])
ID = r"^[0-9a-f]{32}$"


def _missing(message: str) -> AppException:
    return AppException(code=404, message=message, status_code=404)


@router.post("/bases", summary="创建知识库")
async def create_knowledge_base(request: BaseCreate) -> Result[BaseInfo]:
    item = await asyncio.to_thread(create_base, request.name)
    return Result.success(BaseInfo(**item))


@router.get("/bases", summary="列出知识库")
async def list_knowledge_bases() -> Result[list[BaseInfo]]:
    items = await asyncio.to_thread(list_bases)
    return Result.success([BaseInfo(**item) for item in items])


@router.delete("/bases/{base_id}", summary="删除知识库")
async def delete_knowledge_base(base_id: Annotated[str, Path(pattern=ID)]) -> Result[None]:
    try:
        await asyncio.to_thread(remove_base, base_id)
    except LookupError as error:
        raise _missing("知识库不存在") from error
    return Result.success(None, "删除成功")


@router.post("/bases/{base_id}/documents", summary="上传知识库文档")
async def upload_knowledge_document(
    base_id: Annotated[str, Path(pattern=ID)],
    file: Annotated[UploadFile, File()],
) -> Result[DocumentInfo]:
    try:
        item = await asyncio.to_thread(save_document, base_id, file.filename, file.file)
    except LookupError as error:
        raise _missing("知识库不存在") from error
    except ValueError as error:
        status_code = 413 if "超过大小限制" in str(error) else 409 if "相同内容" in str(error) else 400
        raise AppException(code=status_code, message=str(error), status_code=status_code) from error
    finally:
        await file.close()
    schedule_document(item["id"])
    return Result.success(DocumentInfo(**item))


@router.get("/bases/{base_id}/documents", summary="列出知识库文档")
async def list_knowledge_documents(base_id: Annotated[str, Path(pattern=ID)]) -> Result[list[DocumentInfo]]:
    if await asyncio.to_thread(get_base, base_id) is None:
        raise _missing("知识库不存在")
    items = await asyncio.to_thread(list_documents, base_id)
    return Result.success([DocumentInfo(**item) for item in items])


@router.get("/bases/{base_id}/search", summary="检索知识库")
async def search_knowledge_base(
    base_id: Annotated[str, Path(pattern=ID)],
    query: Annotated[str, Query(min_length=1, max_length=2000)],
) -> Result[list[SearchHit]]:
    try:
        items = await search_knowledge(base_id, query)
    except ValueError as error:
        raise _missing("知识库不存在") from error
    return Result.success([SearchHit(**item) for item in items])


@router.get("/documents/{document_id}", summary="查看知识库文档")
async def get_knowledge_document(document_id: Annotated[str, Path(pattern=ID)]) -> Result[DocumentInfo]:
    item = await asyncio.to_thread(get_document, document_id)
    if item is None:
        raise _missing("文档不存在")
    return Result.success(DocumentInfo(**item))


@router.get("/documents/{document_id}/chunks", summary="预览文档切片")
async def get_knowledge_chunks(document_id: Annotated[str, Path(pattern=ID)]) -> Result[list[ChunkInfo]]:
    if await asyncio.to_thread(get_document, document_id) is None:
        raise _missing("文档不存在")
    items = await asyncio.to_thread(list_chunks, document_id)
    return Result.success([ChunkInfo(**item) for item in items])


@router.get("/documents/{document_id}/file", summary="预览或下载原文档")
async def get_knowledge_file(document_id: Annotated[str, Path(pattern=ID)]) -> FileResponse:
    item = await asyncio.to_thread(get_document, document_id)
    if item is None:
        raise _missing("文档不存在")
    source = document_path(item["base_id"], document_id)
    if not source.is_file():
        raise _missing("原文档不存在")
    inline = item["suffix"] in {".pdf", ".txt", ".md", ".markdown"}
    return FileResponse(
        source,
        filename=item["name"],
        content_disposition_type="inline" if inline else "attachment",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/documents/{document_id}/retry", summary="重新索引文档")
async def retry_knowledge_document(document_id: Annotated[str, Path(pattern=ID)]) -> Result[DocumentInfo]:
    item = await asyncio.to_thread(get_document, document_id)
    if item is None:
        raise _missing("文档不存在")
    if item["status"] not in {"failed", "ready"}:
        raise AppException(code=409, message="文档正在处理中", status_code=409)
    await asyncio.to_thread(set_document_status, document_id, "pending")
    schedule_document(document_id)
    item = await asyncio.to_thread(get_document, document_id)
    return Result.success(DocumentInfo(**item))


@router.delete("/documents/{document_id}", summary="删除知识库文档")
async def delete_knowledge_document(document_id: Annotated[str, Path(pattern=ID)]) -> Result[None]:
    try:
        await asyncio.to_thread(remove_document, document_id)
    except LookupError as error:
        raise _missing("文档不存在") from error
    return Result.success(None, "删除成功")
