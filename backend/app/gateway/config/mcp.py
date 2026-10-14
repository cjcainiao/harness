# MCP 服务器配置接口

import asyncio

from fastapi import APIRouter, Response

from app.exceptions import AppException
from app.schemas.config.mcp_schema import (
    MCPServerConfigInfo,
    MCPServerCreate,
    MCPServerEnabledPatch,
    MCPServerPatch,
    MCPStatusInfo,
)
from app.schemas.result import Result
from app.services.config.mcp_service import (
    create_mcp_server,
    delete_mcp_server,
    list_mcp_server_configs,
    read_mcp_status,
    refresh_mcp_status,
    set_mcp_server_enabled,
    update_mcp_server,
)


router = APIRouter(prefix="/mcp", tags=["MCP 服务器"])


# 读取缓存中的服务器状态
@router.get("/status", summary="查询 MCP 服务器状态")
async def get_mcp_status_info(response: Response) -> Result[MCPStatusInfo]:
    response.headers["Cache-Control"] = "no-store"
    return Result.success(read_mcp_status())


# 刷新服务器连接与工具
@router.post("/refresh", summary="刷新 MCP 服务器工具")
async def refresh_mcp_servers(response: Response) -> Result[MCPStatusInfo]:
    response.headers["Cache-Control"] = "no-store"
    return Result.success(await refresh_mcp_status())


# 获取服务器配置列表
@router.get("/servers", summary="获取 MCP 服务器配置")
async def get_mcp_server_configs(response: Response) -> Result[list[MCPServerConfigInfo]]:
    response.headers["Cache-Control"] = "no-store"
    servers = await asyncio.to_thread(list_mcp_server_configs)
    return Result.success(servers)


# 新增服务器配置
@router.post("/servers", summary="新增 MCP 服务器")
async def post_mcp_server(body: MCPServerCreate, response: Response) -> Result[MCPServerConfigInfo]:
    response.headers["Cache-Control"] = "no-store"
    try:
        server = await asyncio.to_thread(
            create_mcp_server, body.name, body.model_dump(exclude={"name"}, exclude_unset=True)
        )
    except FileExistsError as error:
        raise AppException(code=409, message="同名 MCP 服务器已存在", status_code=409) from error
    except ValueError as error:
        raise AppException(code=422, message="服务器配置无效，无法添加", status_code=422) from error
    return Result.success(server)


# 修改服务器配置
@router.patch("/servers/{name}", summary="修改 MCP 服务器")
async def patch_mcp_server(
    name: str, body: MCPServerPatch, response: Response
) -> Result[MCPServerConfigInfo]:
    response.headers["Cache-Control"] = "no-store"
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise AppException(code=422, message="请填写需要修改的配置", status_code=422)
    try:
        server = await asyncio.to_thread(update_mcp_server, name, changes)
    except LookupError as error:
        raise AppException(code=404, message="指定的 MCP 服务器不存在", status_code=404) from error
    except ValueError as error:
        raise AppException(code=422, message="服务器配置无效，无法保存修改", status_code=422) from error
    return Result.success(server)


# 修改服务器启停状态
@router.patch("/servers/{name}/enabled", summary="启用或停用 MCP 服务器")
async def patch_mcp_server_enabled(
    name: str, body: MCPServerEnabledPatch, response: Response
) -> Result[MCPServerConfigInfo]:
    response.headers["Cache-Control"] = "no-store"
    try:
        server = await asyncio.to_thread(set_mcp_server_enabled, name, body.enabled)
    except LookupError as error:
        raise AppException(code=404, message="指定的 MCP 服务器不存在", status_code=404) from error
    except ValueError as error:
        raise AppException(code=422, message="服务器配置无效，无法切换启用状态", status_code=422) from error
    return Result.success(server)


# 删除服务器配置
@router.delete("/servers/{name}", summary="删除 MCP 服务器")
async def remove_mcp_server(name: str, response: Response) -> Result[None]:
    response.headers["Cache-Control"] = "no-store"
    try:
        await asyncio.to_thread(delete_mcp_server, name)
    except LookupError as error:
        raise AppException(code=404, message="指定的 MCP 服务器不存在", status_code=404) from error
    except ValueError as error:
        raise AppException(code=422, message="服务器配置格式不正确，无法删除", status_code=422) from error
    return Result.success(None, "删除成功")
