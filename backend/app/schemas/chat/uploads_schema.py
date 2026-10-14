# 上传附件结构

from pydantic import BaseModel, ConfigDict, Field


# 上传附件信息
class UploadInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: str = Field(description="服务端生成的附件标识")
    thread_id: str = Field(description="所属会话标识")
    name: str = Field(description="原始文件名")
    size: int = Field(description="文件字节数")
    mime_type: str = Field(description="文件媒体类型")
    created_at: str = Field(description="上传时间，ISO-8601 UTC")
    preview_url: str = Field(description="附件预览或下载地址")
