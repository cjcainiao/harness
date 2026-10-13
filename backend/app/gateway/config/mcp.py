# MCP 服务器状态与配置管理接口

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Response

from app.exceptions import AppException
from app.schemas.config.mcp import (
    MCPServerConfigInfo,
    MCPServerCreate,
    MCPServerEnabledPatch,
    MCPServerPatch,
    MCPStatusInfo,
)
from app.schemas.result import Result
from app.services.config.mcp import (
    MCPConfigManagementError,
    create_mcp_server,
    delete_mcp_server,
    list_mcp_server_configs,
    status_info,
    update_mcp_server,
)
from harness.config.app_config import get_app_config
from harness.mcp.cache import get_mcp_status, refresh_mcp_discoveries


router = APIRouter(prefix="/mcp", tags=["MCP 服务器"])


# 查询缓存中的发现状态
@router.get("/status", summary="查询 MCP 服务器状态")
async def get_mcp_servers(response: Response) -> Result[MCPStatusInfo]:
    response.headers["Cache-Control"] = "no-store"
    config = get_app_config().mcp
    return Result.success(status_info(config, get_mcp_status(config)))


# 强制重新发现全部 MCP 服务器
@router.post("/refresh", summary="刷新 MCP 服务器工具")
async def refresh_mcp_servers(response: Response) -> Result[MCPStatusInfo]:
    response.headers["Cache-Control"] = "no-store"
    config = get_app_config().mcp
    snapshot = await refresh_mcp_discoveries(config)
    return Result.success(status_info(config, snapshot))


# 转换配置管理错误
def _config_error(error: MCPConfigManagementError) -> AppException:
    return AppException(code=error.status_code, message=str(error), status_code=error.status_code)


# 查询不含凭据的服务器配置
@router.get("/servers", summary="获取 MCP 服务器配置")
async def get_mcp_server_configs(response: Response) -> Result[list[MCPServerConfigInfo]]:
    response.headers["Cache-Control"] = "no-store"
    try:
        servers = await asyncio.to_thread(list_mcp_server_configs)
    except MCPConfigManagementError as error:
        raise _config_error(error) from error
    return Result.success(servers)


# 新增 MCP 服务器
@router.post("/servers", summary="新增 MCP 服务器")
async def add_mcp_server(request: MCPServerCreate) -> Result[MCPServerConfigInfo]:
    try:
        server = await asyncio.to_thread(
            create_mcp_server, request.name, request.model_dump(exclude={"name"})
        )
    except MCPConfigManagementError as error:
        raise _config_error(error) from error
    return Result.success(server)


# 修改 MCP 服务器
@router.patch("/servers/{name}", summary="修改 MCP 服务器")
async def patch_mcp_server(name: str, request: MCPServerPatch) -> Result[MCPServerConfigInfo]:
    changes = request.model_dump(exclude_unset=True)
    if not changes:
        raise AppException(code=422, message="没有需要修改的字段", status_code=422)
    try:
        server = await asyncio.to_thread(update_mcp_server, name, changes)
    except MCPConfigManagementError as error:
        raise _config_error(error) from error
    return Result.success(server)


# 启用或停用 MCP 服务器
@router.patch("/servers/{name}/enabled", summary="启用或停用 MCP 服务器")
async def set_mcp_server_enabled(name: str, request: MCPServerEnabledPatch) -> Result[MCPServerConfigInfo]:
    try:
        server = await asyncio.to_thread(update_mcp_server, name, {"enabled": request.enabled})
    except MCPConfigManagementError as error:
        raise _config_error(error) from error
    return Result.success(server)


# 删除 MCP 服务器
@router.delete("/servers/{name}", summary="删除 MCP 服务器")
async def remove_mcp_server(name: str) -> Result[None]:
    try:
        await asyncio.to_thread(delete_mcp_server, name)
    except MCPConfigManagementError as error:
        raise _config_error(error) from error
    return Result.success(None, "删除成功")
