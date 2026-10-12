# 技能配置

from pydantic import BaseModel, Field


# 技能配置类
class skillsConfig(BaseModel):
    enabled: bool = Field(default=True, description="是否启用技能")
    dir: str = Field(default="skills", min_length=1, description="技能根目录，相对路径按后端项目根解析")
    file: str = Field(default="SKILL.md", min_length=1, description="技能主文件名")
    categories: list[str] = Field(
        default_factory=lambda: ["custom", "public"],
        min_length=1,
        description="技能分类目录，靠前的优先",
    )
    name_pattern: str = Field(default=r"^[a-z0-9][a-z0-9-]*$", min_length=1, description="技能名字符集")
    description_limit: int = Field(default=1024, gt=0, description="描述字数上限")
    max_download_bytes: int = Field(default=104857600, gt=0, description="技能压缩包文件字节上限")
    max_archive_entries: int = Field(default=10000, gt=0, description="技能压缩包条目数量上限")
    max_unpacked_bytes: int = Field(default=524288000, gt=0, description="技能压缩包解压字节上限")
    max_skill_file_bytes: int = Field(default=1048576, gt=0, description="技能主文件字节上限")
