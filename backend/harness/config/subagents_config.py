# 子代理配置

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# 可用工具名单，写 inherit 表示不限
ToolScope = Literal["inherit"] | list[str]


# 子代理共用默认值
class SubagentDefaults(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    model: str | None = Field(default=None, min_length=1, description="使用的模型，inherit 表示跟随本轮主代理，不填表示默认模型")
    max_turns: int = Field(default=20, gt=0, description="模型调用次数上限")
    timeout_seconds: int = Field(default=180, gt=0, description="单次委派超时时间（秒）")
    tools: ToolScope = Field(default="inherit", description="可用工具名单，[] 表示一个都不给")
    disallowed_tools: list[str] = Field(
        default_factory=lambda: ["task"],
        description="禁用工具名单",
    )


# 单个子代理配置
class SubagentItem(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(min_length=1, description="子代理名称")
    use: str = Field(min_length=1, description="子代理定义实现")
    model: str | None = Field(default=None, min_length=1, description="本条使用的模型")
    max_turns: int | None = Field(default=None, gt=0, description="模型调用次数上限")
    timeout_seconds: int | None = Field(default=None, gt=0, description="单次委派超时时间（秒）")
    tools: ToolScope | None = Field(default=None, description="本条可用工具名单，[] 表示一个都不给")
    disallowed_tools: list[str] | None = Field(default=None, description="本条禁用工具名单")


# 子代理配置类
class subagentsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    enabled: bool = Field(default=True, description="是否启用子代理")
    defaults: SubagentDefaults = Field(default_factory=SubagentDefaults, description="子代理共用默认值")
    items: list[SubagentItem] = Field(default_factory=list, description="子代理列表")
