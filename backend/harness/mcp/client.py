# MCP 客户端与 LangChain 适配器

from __future__ import annotations

from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport, StreamableHttpTransport
from langchain.mcp import MCPAdapter

from harness.config.mcp_config import MCPServerConfig


# 客户端配置错误
class MCPClientConfigError(ValueError):
    pass


# 按连接方式创建客户端
def create_adapter(config: MCPServerConfig) -> MCPAdapter:
    if not config.enabled:
        raise MCPClientConfigError("MCP 服务器尚未启用")

    # 未解析凭据变量拦截
    values = config.headers.values() if config.transport == "streamable_http" else config.env.values()
    if any(value.startswith("$") or "${" in value for value in values):
        raise MCPClientConfigError("MCP 服务器的环境变量引用尚未解析")

    if config.transport == "streamable_http":
        if not config.url:
            raise MCPClientConfigError("streamable_http MCP 服务器缺少 url")
        transport = StreamableHttpTransport(config.url, headers=config.headers)
    elif config.transport == "stdio":
        if not config.command:
            raise MCPClientConfigError("stdio MCP 服务器缺少 command")
        cwd = _resolve_cwd(config.cwd)
        transport = StdioTransport(
            command=config.command,
            args=config.args,
            env=config.env or None,
            cwd=cwd,
            keep_alive=False,
        )
    else:
        raise MCPClientConfigError("MCP 服务器连接方式不受支持")

    client = Client(
        transport,
        timeout=config.call_timeout_seconds,
        init_timeout=config.connect_timeout_seconds,
    )
    return MCPAdapter(client)


# 相对工作目录解析
def _resolve_cwd(value: str | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    path = path.resolve()
    if not path.is_dir():
        raise MCPClientConfigError("stdio MCP 服务器工作目录不存在")
    return str(path)
