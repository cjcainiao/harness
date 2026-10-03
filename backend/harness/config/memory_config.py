# 记忆配置

from typing import Literal

from pydantic import BaseModel, Field


# 记忆配置类
class memoryConfig(BaseModel):
    enabled: bool = Field(default=True, description="是否启用短期记忆")
    type: Literal["sqlite"] = Field(default="sqlite", description="检查点存储类型")
    db_path: str = Field(default="data/checkpoints.db", min_length=1, description="检查点库文件路径，相对路径按后端项目根解析")
    durability: Literal["sync", "async", "exit"] = Field(default="async", description="检查点写盘时机")
