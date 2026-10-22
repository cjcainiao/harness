# 生成图片接口结构

from pydantic import BaseModel, ConfigDict, Field


# 会话中的生成图片摘要
class GeneratedImageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_id: str = Field(description="生成图片标识")
    mime_type: str = Field(description="生成图片格式")
    width: int = Field(description="图片宽度")
    height: int = Field(description="图片高度")
