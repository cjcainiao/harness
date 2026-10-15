# 会话追问推荐配置

from pydantic import BaseModel, ConfigDict, Field


# 会话追问推荐配置类
class RecommendationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    enabled: bool = Field(default=False, description="是否启用会话追问推荐")
    model_name: str | None = Field(
        default=None,
        min_length=1,
        description="推荐模型名称；null 表示使用本轮对话模型",
    )
    count: int = Field(default=3, ge=1, le=3, description="每轮推荐的问题数量，1 到 3 条")
    max_question_length: int = Field(
        default=120,
        gt=0,
        description="每条推荐问题的最大字符数",
    )
    recent_turns: int = Field(
        default=3,
        ge=0,
        description="参考的上一轮已完成对话数量；0 表示只看本轮",
    )
    max_input_tokens: int = Field(
        default=4000,
        gt=0,
        description="传给推荐模型的输入估算 Token 上限",
    )
    timeout_seconds: int = Field(
        default=8,
        gt=0,
        description="推荐模型调用超时时间（秒）",
    )
