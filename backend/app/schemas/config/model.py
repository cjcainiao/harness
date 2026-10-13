# 模型配置接口模型

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# 模型配置列表项
class ModelConfigItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(description="实际模型名称")
    display_name: str = Field(description="模型显示名称")
    description: str | None = Field(description="模型描述")
    provider: str = Field(description="模型厂商")
    use: str = Field(description="模型实现类")
    base_url_configured: bool = Field(description="是否配置服务地址")
    api_key_configured: bool = Field(description="是否配置服务密钥")
    timeout: float | None = Field(description="请求超时时间")
    max_retries: int | None = Field(description="最大重试次数")
    max_tokens: int | None = Field(description="最大输出令牌数")
    supports_thinking: bool = Field(description="是否支持推理")
    reasoning_levels: list[str] = Field(description="模型支持的推理强度")
    when_thinking_enabled: dict[str, Any] | None = Field(description="启用推理参数")
    when_thinking_disabled: dict[str, Any] | None = Field(description="关闭推理参数")
    supports_vision: bool = Field(description="是否支持视觉")
    context_window: int | None = Field(description="模型上下文长度")
