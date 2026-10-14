# MCP 服务器配置请求与响应结构

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt


# 不含连接凭据的服务器配置
class MCPServerConfigInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="服务器名称")
    description: str | None = Field(description="服务器用途说明")
    enabled: bool = Field(description="是否启用服务器")
    transport: Literal["streamable_http", "stdio"] = Field(description="连接方式")
    url: str | None = Field(description="不含凭据和查询参数的服务器地址")
    has_hidden_url: bool = Field(description="服务器地址是否包含隐藏部分")
    header_names: list[str] = Field(description="已配置的请求头名称")
    command_configured: bool = Field(description="是否已配置本地启动命令")
    args_count: int = Field(description="本地启动参数数量")
    env_names: list[str] = Field(description="已配置的环境变量名称")
    cwd_configured: bool = Field(description="是否已配置本地工作目录")
    connect_timeout_seconds: float = Field(description="连接超时时间（秒）")
    call_timeout_seconds: float = Field(description="工具调用超时时间（秒）")


# 新增服务器请求
class MCPServerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$", description="服务器名称")
    description: str | None = Field(default=None, max_length=500, description="服务器用途说明")
    enabled: StrictBool = Field(default=False, description="是否启用服务器")
    transport: Literal["streamable_http", "stdio"] = Field(description="连接方式")
    url: str | None = Field(default=None, description="远程服务器地址")
    headers: dict[str, str] = Field(default_factory=dict, description="远程服务器请求头")
    command: str | None = Field(default=None, description="本地服务器启动命令")
    args: list[str] = Field(default_factory=list, description="本地服务器启动参数")
    env: dict[str, str] = Field(default_factory=dict, description="本地服务器环境变量")
    cwd: str | None = Field(default=None, description="本地服务器工作目录")
    connect_timeout_seconds: StrictInt | StrictFloat = Field(default=10, gt=0, description="连接超时时间（秒）")
    call_timeout_seconds: StrictInt | StrictFloat = Field(default=60, gt=0, description="工具调用超时时间（秒）")


# 修改服务器请求
class MCPServerPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, max_length=500, description="服务器用途说明，传 null 清除")
    enabled: StrictBool | None = Field(default=None, description="是否启用服务器")
    transport: Literal["streamable_http", "stdio"] | None = Field(default=None, description="连接方式")
    url: str | None = Field(default=None, description="远程服务器地址，传 null 清除")
    headers: dict[str, str | None] | None = Field(
        default=None, description="请求头增量，值为 null 时删除，整体为 null 时清空"
    )
    command: str | None = Field(default=None, description="本地服务器启动命令，传 null 清除")
    args: list[str] | None = Field(default=None, description="本地服务器启动参数")
    env: dict[str, str | None] | None = Field(
        default=None, description="环境变量增量，值为 null 时删除，整体为 null 时清空"
    )
    cwd: str | None = Field(default=None, description="本地服务器工作目录，传 null 清除")
    connect_timeout_seconds: StrictInt | StrictFloat | None = Field(
        default=None, gt=0, description="连接超时时间（秒）"
    )
    call_timeout_seconds: StrictInt | StrictFloat | None = Field(
        default=None, gt=0, description="工具调用超时时间（秒）"
    )


# 服务器启停请求
class MCPServerEnabledPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: StrictBool = Field(description="是否启用服务器")


# 单台服务器的工具发现状态
class MCPServerStatusInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="服务器名称")
    enabled: bool = Field(description="是否启用服务器")
    state: Literal["unchecked", "connected", "failed", "disabled"] = Field(description="工具发现状态")
    tool_count: int = Field(description="已发现的工具数量")
    tool_names: list[str] = Field(description="可供代理调用的工具名称")
    error_type: Literal["config", "connection", "timeout"] | None = Field(description="失败原因分类")
    message: str | None = Field(description="失败原因说明")


# 全部服务器的工具发现状态
class MCPStatusInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checked_at: datetime | None = Field(description="最近一次完成工具发现的时间，UTC")
    servers: list[MCPServerStatusInfo] = Field(description="服务器状态列表")
