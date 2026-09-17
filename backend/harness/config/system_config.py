# 系统配置

from typing import Literal

from pydantic import BaseModel, Field


# 系统配置类
class systemConfig(BaseModel):
    app_name: str = Field(default="harness", min_length=1, description="应用名称")
    env: Literal["dev", "test", "prod"] = Field(default="dev", description="运行环境")
    debug: bool = Field(default=False, description="是否开启调试模式")
    host: str = Field(default="127.0.0.1", min_length=1, description="服务监听地址")
    port: int = Field(default=8000, ge=1, le=65535, description="服务监听端口")
    api_prefix: str = Field(default="/api", min_length=1, description="接口统一前缀")
    allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        min_length=1,
        description="允许的请求来源",
    )
    allow_credentials: bool = Field(default=True, description="是否允许携带身份凭证")
    allow_methods: list[str] = Field(default_factory=lambda: ["*"], min_length=1, description="允许的请求方法")
    allow_headers: list[str] = Field(default_factory=lambda: ["*"], min_length=1, description="允许的请求头")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="日志级别")
    log_dir: str = Field(default="logs", min_length=1, description="日志目录，相对路径按后端项目根解析")
    log_max_bytes: int = Field(default=10 * 1024 * 1024, ge=0, description="单个日志文件上限（字节），0 表示不滚动")
    log_backup_count: int = Field(default=7, ge=0, description="滚动保留的历史文件数，0 表示只保留当前文件")
    log_console: bool | None = Field(default=None, description="是否输出到控制台，留空则按 env 自动（prod 关闭）")
