# 知识库请求与响应结构

from pydantic import BaseModel, ConfigDict, Field


class BaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100, description="知识库名称")


class BaseInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="知识库标识")
    name: str = Field(description="知识库名称")
    created_at: str = Field(description="创建时间")
    document_count: int = Field(default=0, description="文档数量")


class DocumentInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="文档标识")
    base_id: str = Field(description="所属知识库标识")
    name: str = Field(description="原文件名")
    sha256: str = Field(description="原文件哈希")
    size: int = Field(description="原文件字节数")
    suffix: str = Field(description="文件格式")
    status: str = Field(description="处理状态")
    error: str | None = Field(description="失败原因")
    chunk_count: int = Field(description="切片数量")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


class ChunkInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(description="切片标识")
    seq: int = Field(description="文档内序号")
    heading: str = Field(description="章节标题")
    content: str = Field(description="切片原文")


class RetrievalInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keyword_rank: int | None = Field(description="关键词召回名次，未命中时为空")
    vector_rank: int | None = Field(description="向量召回名次，未命中时为空")
    rrf_score: float = Field(description="两路排名融合后的分数")
    final_rank: int = Field(description="最终结果名次")


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(description="切片标识")
    document_id: str = Field(description="文档标识")
    document_name: str = Field(description="文档名称")
    heading: str = Field(description="章节标题")
    content: str = Field(description="切片原文")
    retrieval: RetrievalInfo = Field(description="检索排名信息")
