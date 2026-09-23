# 工具配置

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# 工具配置类
class ToolConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    tool_groups: list[dict[str, str]] = Field(default_factory=list, description="工具分组")
    tools: list[dict[str, Any]] = Field(default_factory=list, description="工具列表")
    tool_search: dict[str, Any] = Field(
        default_factory=lambda: {"enabled": False, "max_results": 5},
        description="工具查找配置",
    )
