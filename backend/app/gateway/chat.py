# 模型对话接口

import asyncio
from typing import Self

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.gateway.uploads import UploadInfo
from app.services.upload_store import UploadStoreError, get_upload, upload_preview_url
from harness.agents.thread_state import UploadedFileInfo
from harness.models.factory import ReasoningEffort, validate_model_options
from harness.runtime.stream import stream_agent


router = APIRouter(prefix="/chat", tags=["模型对话"])


# 本轮上传附件信息
class ChatAttachment(UploadInfo):
    file_id: str = Field(pattern=r"^[0-9a-f]{32}$", description="服务端生成的附件标识")


# 模型对话请求
class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=20_000, description="用户消息")
    thread_id: str | None = Field(default=None, min_length=1, max_length=128, description="会话ID")
    attachments: list[ChatAttachment] = Field(default_factory=list, description="本轮上传附件信息")
    model_name: str | None = Field(default=None, min_length=1, max_length=100, description="实际模型名称")
    thinking_enabled: bool = Field(default=False, description="是否启用推理")
    reasoning_effort: ReasoningEffort | None = Field(
        default=None, min_length=1, max_length=32, description="推理程度，取值由所选模型决定"
    )

    # 校验推理参数
    @model_validator(mode="after")
    def validate_options(self) -> Self:
        if self.reasoning_effort is not None and not self.thinking_enabled:
            raise ValueError("设置推理程度前必须启用推理")
        if self.attachments and self.thread_id is None:
            raise ValueError("携带附件时必须指定 thread_id")
        return self


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
