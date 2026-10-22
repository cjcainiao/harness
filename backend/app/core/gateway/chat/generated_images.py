# 生成图片预览与下载接口

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query
from fastapi.responses import FileResponse

from app.core.exceptions import AppException
from app.core.schemas.chat.generated_images_schema import GeneratedImageInfo
from app.core.schemas.result import Result
from app.core.services.chat.generated_images_service import (
    find_generated_image,
    list_thread_generated_images,
)


router = APIRouter(prefix="/images", tags=["生成图片"])


# 会话生成图片清单
@router.get("", summary="获取会话生成图片")
async def get_thread_generated_images(
    thread_id: Annotated[str, Query(min_length=1, max_length=128)],
) -> Result[list[GeneratedImageInfo]]:
    try:
        images = await list_thread_generated_images(thread_id)
    except LookupError as error:
        raise AppException(code=404, message="会话不存在", status_code=404) from error
    return Result.success([GeneratedImageInfo(**item) for item in images])


# 生成图片文件响应
async def _image_response(image_id: str, thread_id: str, *, download: bool) -> FileResponse:
    try:
        stored = await find_generated_image(thread_id, image_id)
    except FileNotFoundError as error:
        raise AppException(code=404, message="生成图片不存在", status_code=404) from error
    return FileResponse(
        stored.path,
        filename=stored.name,
        media_type=stored.mime_type,
        content_disposition_type="attachment" if download else "inline",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


# 预览生成图片
@router.get("/{image_id}/preview", summary="预览生成图片")
async def preview_generated_image(
    image_id: Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")],
    thread_id: Annotated[str, Query(min_length=1, max_length=128)],
) -> FileResponse:
    return await _image_response(image_id, thread_id, download=False)


# 下载生成图片
@router.get("/{image_id}/download", summary="下载生成图片")
async def download_generated_image(
    image_id: Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")],
    thread_id: Annotated[str, Query(min_length=1, max_length=128)],
) -> FileResponse:
    return await _image_response(image_id, thread_id, download=True)
