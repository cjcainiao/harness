# 上下文压缩配置

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


# 消息范围与触发阈值
class ContextSize(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["tokens", "messages", "fraction"] = Field(
        description="计量方式：tokens 令牌数 / messages 消息条数 / fraction 本轮对话模型上下文比例"
    )
    value: int | float = Field(
        description="tokens/messages 使用大于 0 的整数；fraction 使用大于 0 且小于 1 的小数"
    )

    # 按计量方式校验取值
    @model_validator(mode="after")
    def validate_value(self) -> Self:
        if self.type == "fraction":
            if type(self.value) is not float or not 0 < self.value < 1:
                raise ValueError("fraction 的 value 必须是大于 0 且小于 1 的小数")
        elif type(self.value) is not int or self.value <= 0:
            raise ValueError(f"{self.type} 的 value 必须是大于 0 的整数")
        return self


# 上下文压缩总配置
class SummarizationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    enabled: bool = Field(default=False, description="是否启用上下文压缩")
    model_name: str | None = Field(
        default=None,
        min_length=1,
        description="摘要模型名称；null 表示使用本轮对话模型",
    )
    trigger: list[ContextSize] = Field(
        default_factory=lambda: [ContextSize(type="tokens", value=32000)],
        min_length=1,
        description="压缩触发条件，满足任意一项即触发",
    )
    keep: ContextSize = Field(
        default_factory=lambda: ContextSize(type="messages", value=20),
        description="压缩后原样保留的最近消息范围",
    )
    trim_tokens_to_summarize: int | None = Field(
        default=12000,
        gt=0,
        description="单次传给摘要模型的历史令牌数上限；null 表示不限制",
    )
