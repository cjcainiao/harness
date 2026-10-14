# 模型配置请求与响应结构

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt


# 新增模型请求
class ModelConfigCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(min_length=1, description="实际模型名称")
    display_name: str | None = Field(default=None, description="模型显示名称")
    description: str | None = Field(default=None, description="模型描述")
    provider: str = Field(min_length=1, description="模型厂商")
    use: str = Field(min_length=1, description="模型实现类")
    base_url: str | None = Field(default=None, description="服务地址")
    api_key: str | None = Field(default=None, description="服务密钥环境变量引用")
    timeout: StrictFloat | StrictInt | None = Field(default=None, gt=0, description="请求超时时间")
    max_retries: StrictInt | None = Field(default=None, ge=0, description="最大重试次数")
    max_tokens: StrictInt | None = Field(default=None, gt=0, description="最大输出令牌数")
    supports_thinking: StrictBool = Field(default=False, description="是否支持推理")
    reasoning_levels: list[str] = Field(default_factory=list, description="模型支持的推理强度")
    when_thinking_enabled: dict[str, Any] | None = Field(default=None, description="启用推理时使用的模型参数")
    when_thinking_disabled: dict[str, Any] | None = Field(default=None, description="关闭推理时使用的模型参数")
    supports_vision: StrictBool = Field(default=False, description="是否支持视觉")
    context_window: StrictInt | None = Field(default=None, gt=0, description="模型上下文长度")


# 修改模型请求
class ModelConfigPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, description="模型显示名称，传 null 清除")
    description: str | None = Field(default=None, description="模型描述，传 null 清除")
    provider: str | None = Field(default=None, description="模型厂商")
    use: str | None = Field(default=None, description="模型实现类")
    base_url: str | None = Field(default=None, description="服务地址，传 null 清除")
    api_key: str | None = Field(default=None, description="服务密钥环境变量引用，传 null 清除")
    timeout: StrictFloat | StrictInt | None = Field(default=None, gt=0, description="请求超时时间，传 null 清除")
    max_retries: StrictInt | None = Field(default=None, ge=0, description="最大重试次数，传 null 清除")
    max_tokens: StrictInt | None = Field(default=None, gt=0, description="最大输出令牌数，传 null 清除")
    supports_thinking: StrictBool | None = Field(default=None, description="是否支持推理")
    reasoning_levels: list[str] | None = Field(default=None, description="模型支持的推理强度")
    when_thinking_enabled: dict[str, Any] | None = Field(default=None, description="启用推理时使用的模型参数，传 null 清除")
    when_thinking_disabled: dict[str, Any] | None = Field(default=None, description="关闭推理时使用的模型参数，传 null 清除")
    supports_vision: StrictBool | None = Field(default=None, description="是否支持视觉")
    context_window: StrictInt | None = Field(default=None, gt=0, description="模型上下文长度，传 null 清除")


# 模型配置列表项
class ModelConfigInfo(BaseModel):
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
    when_thinking_enabled: dict[str, Any] | None = Field(description="启用推理时使用的模型参数")
    when_thinking_disabled: dict[str, Any] | None = Field(description="关闭推理时使用的模型参数")
    supports_vision: bool = Field(description="是否支持视觉")
    context_window: int | None = Field(description="模型上下文长度")
