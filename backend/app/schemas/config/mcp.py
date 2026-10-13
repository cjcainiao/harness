# MCP 服务器管理接口模型

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from harness.config.mcp_config import MCPServerConfig


# 单台服务器的最近一次发现结果
class MCPServerInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="服务器名称")
    enabled: bool = Field(description="是否启用")
    state: Literal["unchecked", "connected", "failed", "disabled"] = Field(description="最近一次工具发现状态")
    tool_count: int = Field(description="发现的工具数量")
    tool_names: list[str] = Field(description="可供代理调用的工具名称")
    error_type: Literal["config", "connection", "timeout"] | None = Field(description="失败原因分类")
    message: str | None = Field(description="失败原因说明")


# 全部服务器的最近一次发现结果
class MCPStatusInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checked_at: datetime | None = Field(description="最近一次完成工具发现的时间，UTC")
    servers: list[MCPServerInfo] = Field(description="服务器状态列表")


# 新增服务器请求
class MCPServerCreate(MCPServerConfig):
    name: str = Field(description="服务器名称")


# 修改服务器请求
class MCPServerPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, max_length=500, description="服务器用途说明，传 null 清除")
    enabled: StrictBool | None = Field(default=None, description="是否启用服务器")
    transport: Literal["streamable_http", "stdio"] | None = Field(default=None, description="连接方式：streamable_http 或 stdio")
    url: str | None = Field(default=None, description="streamable_http 服务器地址，传 null 清除")
    headers: dict[str, str | None] | None = Field(default=None, description="请求头增量，值为 null 时删除，整体为 null 时清空")
    command: str | None = Field(default=None, description="本地服务器启动命令，传 null 清除")
    args: list[str] | None = Field(default=None, description="本地服务器启动参数")
    env: dict[str, str | None] | None = Field(default=None, description="环境变量增量，值为 null 时删除，整体为 null 时清空")
    cwd: str | None = Field(default=None, description="本地服务器工作目录，传 null 清除")
    connect_timeout_seconds: float | None = Field(default=None, description="连接超时时间（秒）")
    call_timeout_seconds: float | None = Field(default=None, description="工具调用超时时间（秒）")


# 启停服务器请求
class MCPServerEnabledPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: StrictBool = Field(description="是否启用服务器")


# 不含凭据的服务器配置
class MCPServerConfigInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="服务器名称")
    description: str | None = Field(description="服务器用途说明")
    enabled: bool = Field(description="是否启用服务器")
    transport: Literal["streamable_http", "stdio"] = Field(description="连接方式")
    url: str | None = Field(description="不含查询参数和凭据的服务器地址")
    has_hidden_url: bool = Field(description="地址是否含有隐藏部分")
    header_names: list[str] = Field(description="已配置的请求头名称")
    command_configured: bool = Field(description="是否已配置本地服务器启动命令")
    args_count: int = Field(description="本地服务器启动参数数量")
    env_names: list[str] = Field(description="已配置的环境变量名称")
    cwd_configured: bool = Field(description="是否已配置本地服务器工作目录")
    connect_timeout_seconds: float = Field(description="连接超时时间（秒）")
    call_timeout_seconds: float = Field(description="工具调用超时时间（秒）")
