# MCP 服务器配置文件管理

from __future__ import annotations

import re
import threading
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from pydantic import ValidationError
from ruamel.yaml.comments import CommentedMap

from app.schemas.config.mcp import MCPServerConfigInfo, MCPServerInfo, MCPStatusInfo
from harness.config.app_config import AppConfig, get_app_config, reload_app_config
from harness.config.mcp_config import MCPConfig
from harness.mcp.cache import MCPStatusSnapshot, reset_mcp_cache
from harness.mcp.tools import mcp_tool_name
from harness.utils.yaml_util import dump_yaml, load_yaml_keep_comment


_write_lock = threading.Lock()
_secret_name = re.compile(r"(?:authorization|api[_-]?key|token|secret|password|credential|auth)", re.I)
_env_reference = re.compile(r"\$(?:\{[A-Za-z_][A-Za-z0-9_]*\}|[A-Za-z_][A-Za-z0-9_]*)")


# 转换为不包含连接凭据的状态数据
def status_info(config: MCPConfig, snapshot: MCPStatusSnapshot) -> MCPStatusInfo:
    servers = [
        MCPServerInfo(
            name=status.name,
            enabled=config.servers[status.name].enabled,
            state=status.state,
            tool_count=len(status.tool_names),
            tool_names=[mcp_tool_name(status.name, name) for name in status.tool_names],
            error_type=status.error_type,
            message=status.message,
        )
        for status in snapshot.servers
    ]
    return MCPStatusInfo(checked_at=snapshot.checked_at, servers=servers)


# 配置管理错误
class MCPConfigManagementError(ValueError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


# 读取配置中的服务器映射
def _read_servers() -> tuple[CommentedMap, CommentedMap]:
    data = load_yaml_keep_comment(AppConfig.resolve_config_path())
    mcp = data.get("mcp")
    if mcp is None:
        mcp = CommentedMap()
        data["mcp"] = mcp
    if not isinstance(mcp, dict):
        raise MCPConfigManagementError(422, "MCP 配置格式无效")
    servers = mcp.get("servers")
    if servers is None:
        servers = CommentedMap()
        mcp["servers"] = servers
    if not isinstance(servers, dict):
        raise MCPConfigManagementError(422, "MCP 服务器列表格式无效")
    return data, servers


# 校验敏感字段使用环境变量引用
def _check_secret_values(values: Mapping[str, Any] | None) -> None:
    if values is None:
        return
    for name, value in values.items():
        if value is not None and _secret_name.search(name) and not _env_reference.search(value):
            raise MCPConfigManagementError(422, f"敏感配置 {name} 必须引用环境变量")


# 阻止地址内直接写入凭据
def _check_url_secret(value: str | None) -> None:
    if value is None or value.startswith("$"):
        return
    try:
        parsed = urlsplit(value)
    except ValueError as error:
        raise MCPConfigManagementError(422, "MCP 地址格式无效") from error
    if parsed.username or parsed.password:
        raise MCPConfigManagementError(422, "MCP 地址不能直接包含用户名或密码")
    for name, item in parse_qsl(parsed.query, keep_blank_values=True):
        _check_secret_values({name: item})


# 隐藏 URL 中可能携带的凭据
def _safe_url(value: str | None) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    if value.startswith("$"):
        return None, True
    try:
        parsed = urlsplit(value)
        hidden = bool(parsed.username or parsed.password or parsed.query or parsed.fragment)
        if parsed.username or parsed.password:
            return None, True
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")), hidden
    except ValueError:
        return None, True


# 转换为不含凭据的服务器配置
def _server_info(name: str, server: Mapping[str, Any]) -> MCPServerConfigInfo:
    config = get_app_config().mcp.servers[name]
    url, has_hidden_url = _safe_url(server.get("url"))
    return MCPServerConfigInfo(
        name=name,
        description=config.description,
        enabled=config.enabled,
        transport=config.transport,
        url=url,
        has_hidden_url=has_hidden_url,
        header_names=list((server.get("headers") or {}).keys()),
        command_configured=bool(server.get("command")),
        args_count=len(server.get("args") or []),
        env_names=list((server.get("env") or {}).keys()),
        cwd_configured=bool(server.get("cwd")),
        connect_timeout_seconds=config.connect_timeout_seconds,
        call_timeout_seconds=config.call_timeout_seconds,
    )


# 验证后写回原始配置并更新运行时缓存
def _save(data: CommentedMap) -> None:
    try:
        candidate = dict(data)
        mcp = candidate.pop("mcp")
        candidate = AppConfig.resolve_env_variables(candidate)
        candidate["mcp"] = AppConfig.resolve_mcp_env_variables(mcp)
        AppConfig.model_validate(candidate)
    except (ValidationError, ValueError, TypeError) as error:
        raise MCPConfigManagementError(422, "MCP 配置无效或引用的环境变量不可用") from error
    dump_yaml(AppConfig.resolve_config_path(), data)
    reload_app_config()
    reset_mcp_cache()


# 列出服务器配置
def list_mcp_server_configs() -> list[MCPServerConfigInfo]:
    _, servers = _read_servers()
    return [_server_info(name, server) for name, server in servers.items()]


# 新增服务器
def create_mcp_server(name: str, values: dict[str, Any]) -> MCPServerConfigInfo:
    with _write_lock:
        data, servers = _read_servers()
        if name in servers:
            raise MCPConfigManagementError(409, f"MCP 服务器已存在：{name}")
        _check_secret_values(values.get("headers"))
        _check_secret_values(values.get("env"))
        _check_url_secret(values.get("url"))
        servers[name] = CommentedMap(values)
        _save(data)
        return _server_info(name, servers[name])


# 合并服务器配置字段
def _merge_server(target: CommentedMap, changes: dict[str, Any]) -> None:
    for field, value in changes.items():
        if field not in {"headers", "env"}:
            if field == "url":
                _check_url_secret(value)
            target[field] = value
            continue
        _check_secret_values(value)
        if value is None:
            target[field] = CommentedMap()
            continue
        current = target.get(field) or CommentedMap()
        for key, item in value.items():
            if item is None:
                current.pop(key, None)
            else:
                current[key] = item
        target[field] = current


# 修改服务器配置
def update_mcp_server(name: str, changes: dict[str, Any]) -> MCPServerConfigInfo:
    with _write_lock:
        data, servers = _read_servers()
        target = servers.get(name)
        if target is None:
            raise MCPConfigManagementError(404, f"MCP 服务器不存在：{name}")
        _merge_server(target, changes)
        _save(data)
        return _server_info(name, target)


# 删除服务器
def delete_mcp_server(name: str) -> None:
    with _write_lock:
        data, servers = _read_servers()
        if name not in servers:
            raise MCPConfigManagementError(404, f"MCP 服务器不存在：{name}")
        del servers[name]
        # 空映射保持行内格式，避免行尾注释后出现顶格的 {}
        if not servers:
            servers.fa.set_flow_style()
        _save(data)
