# 文件上传、预览和删除接口

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, File, Form, Path, Query, UploadFile
from fastapi.responses import FileResponse

from app.exceptions import AppException
from app.schemas.chat.uploads import UploadInfo
from app.schemas.result import Result
from app.services.chat.uploads import (
    INLINE_IMAGE_TYPES,
    UploadStoreError,
    delete_upload,
    get_upload,
    save_upload,
    upload_preview_url,
)


router = APIRouter(prefix="/uploads", tags=["文件上传"])


# 上传错误转换
def _upload_error(error: UploadStoreError) -> AppException:
    return AppException(code=error.status_code, message=str(error), status_code=error.status_code)


# 会话文件上传
@router.post("", summary="上传文件")
async def create_upload(
    thread_id: Annotated[str, Form(min_length=1, max_length=128)],
    file: Annotated[UploadFile, File()],
) -> Result[UploadInfo]:
    try:
        stored = await asyncio.to_thread(save_upload, thread_id, file.filename, file.file)
    except UploadStoreError as error:
        raise _upload_error(error) from error
    finally:
        await file.close()

    return Result.success(
        UploadInfo(
            file_id=stored.file_id,
            thread_id=stored.thread_id,
            name=stored.name,
            size=stored.size,
            mime_type=stored.mime_type,
            created_at=stored.created_at,
            preview_url=upload_preview_url(thread_id, stored.file_id),
        )
    )


# 附件预览与下载
@router.get("/{file_id}/preview", summary="预览或下载文件")
async def preview_upload(
    file_id: Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")],
    thread_id: Annotated[str, Query(min_length=1, max_length=128)],
) -> FileResponse:
    try:
        stored = await asyncio.to_thread(get_upload, thread_id, file_id)
    except UploadStoreError as error:
        raise _upload_error(error) from error

    inline = stored.mime_type in INLINE_IMAGE_TYPES
    return FileResponse(
        stored.path,
        filename=stored.name,
        media_type=stored.mime_type if inline else "application/octet-stream",
        content_disposition_type="inline" if inline else "attachment",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


# 会话附件删除
@router.delete("/{file_id}", summary="删除上传文件")
async def remove_upload(
    file_id: Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")],
    thread_id: Annotated[str, Query(min_length=1, max_length=128)],
) -> Result[None]:
    try:
        await asyncio.to_thread(delete_upload, thread_id, file_id)
    except UploadStoreError as error:
        raise _upload_error(error) from error
    return Result.success(None, "删除成功")
