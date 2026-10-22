# 技能包配置请求与响应结构

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


# 技能包列表项
class SkillConfigInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="技能名称")
    description: str = Field(description="技能说明")
    source: Literal["custom", "public"] = Field(description="技能来源")
    enabled: bool = Field(description="技能是否启用")


# 技能启停请求
class SkillEnabledPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: StrictBool = Field(description="是否启用技能")
