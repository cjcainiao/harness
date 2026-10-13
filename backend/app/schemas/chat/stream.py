# 对话请求结构

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.chat.uploads import UploadInfo
from harness.models.factory import ReasoningEffort


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
