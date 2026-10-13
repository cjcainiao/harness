# 模型配置接口模型

from pydantic import BaseModel, ConfigDict, Field


# 模型信息
class ModelInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(description="实际模型名称")
    display_name: str = Field(description="模型显示名称")
    description: str | None = Field(default=None, description="模型描述")
    provider: str = Field(description="模型厂商")
    use: str = Field(description="模型实现类")
    supports_thinking: bool = Field(default=False, description="是否支持推理")
    reasoning_levels: list[str] = Field(default_factory=list, description="模型支持的推理强度")
    supports_vision: bool = Field(default=False, description="是否支持视觉")
    context_window: int | None = Field(default=None, description="模型上下文长度")
