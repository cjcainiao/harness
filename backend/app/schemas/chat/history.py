# 会话历史结构

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chat.uploads import UploadInfo


# 轮次渲染段
class TurnItemInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(description="段类型，取值 message / reasoning / tool / error")
    content: str | None = Field(default=None, description="正文、推理或失败提示文本")
    duration_ms: int | None = Field(default=None, description="本段耗时，单位毫秒")
    tool: str | None = Field(default=None, description="工具名称")
    tool_call_id: str | None = Field(default=None, description="工具调用标识")
    status: str | None = Field(
        default=None, description="工具状态，取值 preparing / running / success / error"
    )
    arguments: dict[str, Any] | str | None = Field(default=None, description="工具入参")
    output: Any = Field(default=None, description="工具返回内容")
    subagent: str | None = Field(default=None, description="执行这段的子代理名称")
    delegation_id: str | None = Field(default=None, description="所属委派标识")


# Token 用量
class UsageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int = Field(description="输入 Token 数")
    output_tokens: int = Field(description="输出 Token 数")
    total_tokens: int = Field(description="总 Token 数")
    cache_read_tokens: int | None = Field(default=None, description="缓存命中的输入 Token 数")
    reasoning_tokens: int | None = Field(default=None, description="推理消耗的输出 Token 数")


# 会话摘要
class ThreadInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str = Field(description="会话标识")
    title: str = Field(description="会话标题")
    created_at: str = Field(description="创建时间，ISO-8601 UTC")
    updated_at: str = Field(description="最后活动时间，ISO-8601 UTC")
    input_tokens: int = Field(description="会话累计输入 Token")
    output_tokens: int = Field(description="会话累计输出 Token")


# 提问正文与附件
class QuestionInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(description="提问正文")
    attachments: list[UploadInfo] = Field(description="本轮上传附件信息")


# 一轮问答
class TurnInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: str = Field(description="轮次标识")
    thread_id: str = Field(description="所属会话")
    seq: int = Field(description="会话内序号")
    question: QuestionInfo = Field(description="提问正文与附件")
    status: str = Field(description="轮次状态，取值 streaming / completed / failed / interrupted")
    created_at: str = Field(description="提问时间，ISO-8601 UTC")
    items: list[TurnItemInfo] = Field(description="渲染段，顺序即显示顺序")
    usage: UsageInfo | None = Field(default=None, description="本轮累计用量")
