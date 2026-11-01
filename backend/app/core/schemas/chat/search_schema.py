# 对话消息检索结构

from pydantic import BaseModel, ConfigDict, Field


# 检索命中的会话
class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str = Field(description="会话标识")
    title: str = Field(description="会话标题")
    updated_at: str = Field(description="最后活动时间，ISO-8601 UTC")
    workspace: str | None = Field(default=None, description="会话工作空间绝对路径，未创建时为空")
