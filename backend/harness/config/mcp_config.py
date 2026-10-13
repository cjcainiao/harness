# MCP 配置

from __future__ import annotations

import re
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator


# 服务器名称格式
_SERVER_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


# 单个 MCP 服务器配置
class MCPServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str | None = Field(default=None, max_length=500, description="服务器用途说明")
    enabled: StrictBool = Field(default=False, description="是否启用服务器")
    transport: Literal["streamable_http", "stdio"] = Field(description="连接方式：streamable_http 或 stdio")
    url: str | None = Field(default=None, min_length=1, description="streamable_http 服务器地址")
    headers: dict[str, str] = Field(default_factory=dict, description="streamable_http 请求头，密钥可引用环境变量")
    command: str | None = Field(default=None, min_length=1, description="本地服务器启动命令")
    args: list[str] = Field(default_factory=list, description="本地服务器启动参数")
    env: dict[str, str] = Field(default_factory=dict, description="本地服务器环境变量")
    cwd: str | None = Field(default=None, min_length=1, description="本地服务器工作目录")
    connect_timeout_seconds: float = Field(default=10, gt=0, description="连接超时时间（秒）")
    call_timeout_seconds: float = Field(default=60, gt=0, description="工具调用超时时间（秒）")

    # 校验 HTTP 地址
    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value.startswith("$"):
            return value
        try:
            parsed = urlsplit(value)
            valid = parsed.scheme in {"http", "https"} and parsed.hostname is not None
            _ = parsed.port
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("streamable_http MCP 服务器地址必须是有效的 http:// 或 https:// URL")
        return value

    # 校验连接方式对应的配置
    @model_validator(mode="after")
    def validate_transport(self) -> Self:
        if self.transport == "streamable_http":
            if self.command is not None or self.args or self.env or self.cwd is not None:
                raise ValueError("streamable_http MCP 服务器不能配置 command、args、env 或 cwd")
            if self.enabled and self.url is None:
                raise ValueError("已启用的 streamable_http MCP 服务器缺少 url")
            if self.enabled and self.url is not None and self.url.startswith("$"):
                raise ValueError("已启用的 streamable_http MCP 服务器 url 环境变量未解析")
        else:
            if self.url is not None or self.headers:
                raise ValueError("stdio MCP 服务器不能配置 url 或 headers")
            if self.enabled and self.command is None:
                raise ValueError("已启用的 stdio MCP 服务器缺少 command")
        return self


# MCP 总配置
class MCPConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    servers: dict[str, MCPServerConfig] = Field(default_factory=dict, description="MCP 服务器列表，以名称为键")

    # 校验服务器名称
    @field_validator("servers")
    @classmethod
    def validate_server_names(cls, servers: dict[str, MCPServerConfig]) -> dict[str, MCPServerConfig]:
        for name in servers:
            if not _SERVER_NAME_PATTERN.fullmatch(name):
                raise ValueError(f"MCP 服务器名称不合规：{name}；只能使用英文字母、数字、下划线和连字符，且须以字母开头")
        return servers
