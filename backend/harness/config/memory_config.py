# 记忆配置

from typing import Literal

from pydantic import BaseModel, Field


# 记忆配置类
class memoryConfig(BaseModel):
    enabled: bool = Field(default=True, description="是否启用短期记忆")
    type: Literal["sqlite"] = Field(default="sqlite", description="检查点存储类型")
    durability: Literal["sync", "async", "exit"] = Field(default="async", description="检查点写盘时机")
