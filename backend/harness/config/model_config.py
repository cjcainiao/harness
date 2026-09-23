# 模型配置

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# 模型配置类
class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(description="模型名称")
    display_name: str | None = Field(default=None, description="模型显示名称")
    description: str | None = Field(default=None, description="模型描述")
    use: str = Field(description="模型实现类")
    model: str = Field(description="服务商模型名称")
    supports_thinking: bool = Field(default=False, description="是否支持推理")
    reasoning_levels: list[str] = Field(default_factory=list, description="模型支持的推理强度")
    when_thinking_enabled: dict | None = Field(default=None, description="启用推理时使用的模型参数")
    when_thinking_disabled: dict | None = Field(default=None, description="关闭推理时使用的模型参数")
    supports_vision: bool = Field(default=False, description="是否支持视觉")
    context_window: int | None = Field(default=None, gt=0, description="模型上下文长度")

    # 清理并校验模型支持的档位
    @field_validator("reasoning_levels")
    @classmethod
    def validate_reasoning_levels(cls, levels: list[str]) -> list[str]:
        normalized = [level.strip() for level in levels]
        if any(not level for level in normalized):
            raise ValueError("推理强度不能是空字符串")
        if len(set(normalized)) != len(normalized):
            raise ValueError("推理强度不能重复")
        return normalized

    # 档位配置依赖推理能力
    @model_validator(mode="after")
    def validate_thinking_support(self) -> Self:
        if self.reasoning_levels and not self.supports_thinking:
            raise ValueError("配置推理强度前必须声明支持推理")
        return self
