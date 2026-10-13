# MCP 服务器工具发现与状态汇总

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal

from langchain_core.tools import BaseTool
from pydantic import ValidationError

from harness.config.app_config import get_app_config
from harness.config.mcp_config import MCPConfig, MCPServerConfig
from harness.core.logger import get_logger
from harness.mcp.client import MCPClientConfigError, create_adapter

logger = get_logger(__name__)


# 单台服务器的发现状态
@dataclass(frozen=True, slots=True)
class MCPServerStatus:
    name: str
    state: Literal["unchecked", "connected", "failed", "disabled"]
    tool_names: tuple[str, ...] = ()
    error_type: Literal["config", "connection", "timeout"] | None = None
    message: str | None = None


# 单台服务器的工具与状态
@dataclass(frozen=True, slots=True)
class MCPServerDiscovery:
    status: MCPServerStatus
    tools: tuple[BaseTool, ...] = ()


# 连接单台服务器并读取工具
async def discover_server(name: str, config: MCPServerConfig) -> MCPServerDiscovery:
    if not config.enabled:
        return MCPServerDiscovery(MCPServerStatus(name=name, state="disabled"))

    try:
        # 服务器配置复核
        validated = MCPServerConfig.model_validate(config.model_dump())
    except ValidationError:
        logger.warning("MCP 服务器配置无效", server=name)
        return MCPServerDiscovery(
            MCPServerStatus(name=name, state="failed", error_type="config", message="MCP 服务器配置字段无效")
        )

    try:
        adapter = create_adapter(validated)
    except MCPClientConfigError as error:
        logger.warning("MCP 服务器配置无效", server=name, error_type=type(error).__name__)
        return MCPServerDiscovery(
            MCPServerStatus(name=name, state="failed", error_type="config", message=str(error))
        )
    except Exception as error:
        return _discovery_failure(name, error)

    try:
        # 连接与工具发现超时
        async with asyncio.timeout(validated.connect_timeout_seconds + validated.call_timeout_seconds):
            tools = tuple(await adapter.list_tools())
    except Exception as error:
        return _discovery_failure(name, error)

    status = MCPServerStatus(name=name, state="connected", tool_names=tuple(tool.name for tool in tools))
    logger.info("MCP 服务器工具发现完成", server=name, tools=status.tool_names)
    return MCPServerDiscovery(status=status, tools=tools)


# 嵌套超时识别
def _is_timeout(error: BaseException) -> bool:
    pending = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, TimeoutError):
            return True
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions)
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        elif current.__context__ is not None:
            pending.append(current.__context__)
    return False


# 底层异常脱敏
def _discovery_failure(name: str, error: Exception) -> MCPServerDiscovery:
    if _is_timeout(error):
        logger.warning("MCP 服务器连接或工具发现超时", server=name)
        return MCPServerDiscovery(
            MCPServerStatus(name=name, state="failed", error_type="timeout", message="连接或读取工具超时")
        )

    exception_name = type(error).__name__
    logger.warning("MCP 服务器连接或工具发现失败", server=name, exception=exception_name)
    return MCPServerDiscovery(
        MCPServerStatus(
            name=name,
            state="failed",
            error_type="connection",
            message=f"连接或读取工具失败（{exception_name}）",
        )
    )


# 服务器并行发现
async def discover_servers(config: MCPConfig | None = None) -> dict[str, MCPServerDiscovery]:
    server_config = config if config is not None else get_app_config().mcp
    names = tuple(server_config.servers)
    results = await asyncio.gather(
        *(discover_server(name, server_config.servers[name]) for name in names)
    )
    return dict(zip(names, results, strict=True))
