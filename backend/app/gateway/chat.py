# 模型对话接口

from typing import Self

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from harness.models.factory import ReasoningEffort, validate_model_options
from harness.runtime.stream import stream_agent


router = APIRouter(prefix="/chat", tags=["模型对话"])


# 模型对话请求
class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=20_000, description="用户消息")
    thread_id: str | None = Field(default=None, min_length=1, max_length=128, description="会话ID")
    model_name: str | None = Field(default=None, min_length=1, max_length=100, description="模型名称")
    thinking_enabled: bool = Field(default=False, description="是否启用推理")
    reasoning_effort: ReasoningEffort | None = Field(
        default=None, min_length=1, max_length=32, description="推理程度，取值由所选模型决定"
    )

    # 校验推理参数
    @model_validator(mode="after")
    def validate_reasoning(self) -> Self:
        if self.reasoning_effort is not None and not self.thinking_enabled:
            raise ValueError("设置推理程度前必须启用推理")
        return self


# 模型流式对话
@router.post("/stream", summary="模型流式对话")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    # 流开始前校验模型选项
    try:
        validate_model_options(
            request.model_name,
            request.thinking_enabled,
            request.reasoning_effort,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return StreamingResponse(
        stream_agent(
            message=request.message,
            thread_id=request.thread_id,
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
