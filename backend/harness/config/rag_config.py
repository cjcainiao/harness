# 知识库配置

from pydantic import BaseModel, ConfigDict, Field


class RagConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files_dir: str = Field(default="data/knowledge", description="知识库原文件目录，相对路径按后端项目根解析")
    upload_max_bytes: int = Field(default=20_971_520, gt=0, description="单个知识库文档的最大字节数")
    embedding_base_url: str = Field(default="", description="向量模型 OpenAI 兼容接口的服务地址")
    embedding_api_key: str = Field(default="", description="向量模型服务密钥")
    embedding_model: str = Field(default="qwen3.7-text-embedding-flash", description="向量模型名称，修改后自动重建文档索引")
    embedding_dimensions: int = Field(default=1024, gt=0, description="向量维度，修改后自动重建文档索引")
    embedding_timeout_seconds: float = Field(default=30.0, gt=0, description="向量接口请求超时秒数")
    chunk_size: int = Field(default=900, gt=0, description="文档切片的最大字符数")
    chunk_overlap: int = Field(default=120, ge=0, description="相邻切片的重叠字符数")
    recall_top_k: int = Field(default=12, gt=0, description="每路检索召回的切片数量")
    answer_top_k: int = Field(default=5, gt=0, description="交给聊天模型的切片数量")
    min_vector_similarity: float = Field(default=0.45, ge=0, le=1, description="向量结果的最低余弦相似度")
    min_keyword_coverage: float = Field(default=0.5, ge=0, le=1, description="仅关键词命中时的最低有效提问词覆盖率")
