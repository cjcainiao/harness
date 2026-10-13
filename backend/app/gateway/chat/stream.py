# 模型对话接口

import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat.stream import ChatAttachment, ChatRequest
from app.services.chat.uploads import UploadStoreError, get_upload, upload_preview_url
from harness.agents.thread_state import UploadedFileInfo
from harness.models.factory import validate_model_options
from harness.runtime.stream import stream_agent


router = APIRouter(tags=["模型对话"])


# 附件归属与元数据
def _uploaded_file_info(thread_id: str, attachments: list[ChatAttachment]) -> list[UploadedFileInfo]:
    uploaded_files: list[UploadedFileInfo] = []
    for item in attachments:
        stored = get_upload(thread_id, item.file_id)
        uploaded_files.append(
            {
                "file_id": stored.file_id,
                "thread_id": stored.thread_id,
                "name": stored.name,
                "size": stored.size,
                "mime_type": stored.mime_type,
                "created_at": stored.created_at,
                "preview_url": upload_preview_url(stored.thread_id, stored.file_id),
            }
        )
    return uploaded_files


# 模型流式对话
@router.post("/stream", summary="模型流式对话")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    # 模型选项校验
    try:
        validate_model_options(
            request.model_name,
            request.thinking_enabled,
            request.reasoning_effort,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    uploaded_files: list[UploadedFileInfo] = []
    if request.thread_id is not None and request.attachments:
        try:
            uploaded_files = await asyncio.to_thread(
                _uploaded_file_info, request.thread_id, request.attachments
            )
        except UploadStoreError as error:
            raise HTTPException(status_code=error.status_code, detail=str(error)) from error

    return StreamingResponse(
        stream_agent(
            message=request.message,
            thread_id=request.thread_id,
            uploaded_files=uploaded_files,
            model_name=request.model_name,
            thinking_enabled=request.thinking_enabled,
            reasoning_effort=request.reasoning_effort,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
