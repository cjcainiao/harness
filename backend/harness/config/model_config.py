# 模型配置

from pydantic import BaseModel, ConfigDict, Field


# 模型配置类
class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(description="模型名称")
    display_name: str | None = Field(default=None, description="模型显示名称")
    description: str | None = Field(default=None, description="模型描述")
    use: str = Field(description="模型实现类")
    model: str = Field(description="服务商模型名称")
    supports_thinking: bool = Field(default=False, description="是否支持推理")
    supports_reasoning_effort: bool = Field(default=False, description="是否支持推理程度")
    when_thinking_enabled: dict | None = Field(default=None, description="启用推理时使用的模型参数")
    when_thinking_disabled: dict | None = Field(default=None, description="关闭推理时使用的模型参数")
    supports_vision: bool = Field(default=False, description="是否支持视觉")
    context_window: int | None = Field(default=None, gt=0, description="模型上下文长度")
