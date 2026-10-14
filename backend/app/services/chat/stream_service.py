# 模型对话业务

import asyncio
from collections.abc import AsyncIterator

from app.schemas.chat.stream_schema import ChatAttachment, ChatRequest
from app.services.chat.uploads_service import get_upload, uploaded_file_info
from harness.agents.thread_state import UploadedFileInfo
from harness.models.factory import validate_model_options
from harness.runtime.stream import stream_agent


# 校验并加载本轮附件
def _uploaded_file_infos(
    thread_id: str, attachments: list[ChatAttachment]
) -> list[UploadedFileInfo]:
    return [uploaded_file_info(get_upload(thread_id, item.file_id)) for item in attachments]


# 准备模型流式对话
async def prepare_chat_stream(request: ChatRequest) -> AsyncIterator[str]:
    validate_model_options(
        request.model_name,
        request.thinking_enabled,
        request.reasoning_effort,
    )

    uploaded_files: list[UploadedFileInfo] = []
    if request.thread_id is not None and request.attachments:
        uploaded_files = await asyncio.to_thread(
            _uploaded_file_infos, request.thread_id, request.attachments
        )

    return stream_agent(
        message=request.message,
        thread_id=request.thread_id,
        uploaded_files=uploaded_files,
        model_name=request.model_name,
        thinking_enabled=request.thinking_enabled,
        reasoning_effort=request.reasoning_effort,
    )
