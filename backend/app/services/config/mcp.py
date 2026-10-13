# MCP 服务器配置文件管理

from __future__ import annotations

import re
import threading
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from app.schemas.config.mcp import MCPServerConfigInfo, MCPServerInfo, MCPStatusInfo
from harness.config.app_config import AppConfig, get_app_config, reload_app_config
from harness.config.mcp_config import MCPConfig
from harness.mcp.cache import MCPStatusSnapshot, reset_mcp_cache
from harness.mcp.tools import mcp_tool_name
from harness.utils.yaml_util import (
    edit_yaml_text,
    load_yaml_keep_comment,
    render_yaml_fragment,
    yaml_block_end,
)


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
    return data, _get_servers(data)


# 取得服务器映射
def _get_servers(data: CommentedMap) -> CommentedMap:
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
    return servers


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


# 校验配置内容
def _validate_config(data: CommentedMap) -> None:
    try:
        candidate = dict(data)
        mcp = candidate.pop("mcp")
        candidate = AppConfig.resolve_env_variables(candidate)
        candidate["mcp"] = AppConfig.resolve_mcp_env_variables(mcp)
        AppConfig.model_validate(candidate)
    except (ValidationError, ValueError, TypeError) as error:
        raise MCPConfigManagementError(422, "MCP 配置无效或引用的环境变量不可用") from error


# 序列化单个服务器配置块
def _render_server(name: str, server: CommentedMap, newline: str) -> str:
    wrapper = CommentedMap({"mcp": CommentedMap({"servers": CommentedMap({name: server})})})
    fragment = render_yaml_fragment(wrapper, newline)
    return "".join(fragment.splitlines(keepends=True)[2:])


# 局部修改配置并刷新缓存
def _edit_config(
    edit: Callable[[str, CommentedMap, CommentedMap, bool, bool], str],
) -> None:
    def apply(source: str) -> str:
        yaml = YAML()
        data = yaml.load(source)
        if not isinstance(data, CommentedMap):
            raise MCPConfigManagementError(422, "配置文件格式无效")
        had_mcp = "mcp" in data
        had_servers = had_mcp and isinstance(data["mcp"], dict) and "servers" in data["mcp"]
        servers = _get_servers(data)
        updated = edit(source, data, servers, had_mcp, had_servers)
        _validate_config(data)
        if yaml.load(updated) != data:
            raise RuntimeError("修改 MCP 后的配置校验失败")
        return updated

    edit_yaml_text(AppConfig.resolve_config_path(), apply)
    reload_app_config()
    reset_mcp_cache()


# 列出服务器配置
def list_mcp_server_configs() -> list[MCPServerConfigInfo]:
    _, servers = _read_servers()
    return [_server_info(name, server) for name, server in servers.items()]


# 新增服务器
def create_mcp_server(name: str, values: dict[str, Any]) -> MCPServerConfigInfo:
    with _write_lock:
        saved: CommentedMap | None = None

        # 在服务器列表末尾插入配置块
        def add_server(
            source: str,
            data: CommentedMap,
            servers: CommentedMap,
            had_mcp: bool,
            had_servers: bool,
        ) -> str:
            nonlocal saved
            if name in servers:
                raise MCPConfigManagementError(409, f"MCP 服务器已存在：{name}")
            _check_secret_values(values.get("headers"))
            _check_secret_values(values.get("env"))
            _check_url_secret(values.get("url"))
            servers[name] = CommentedMap(values)
            saved = servers[name]
            newline = "\r\n" if "\r\n" in source else "\n"
            lines = source.splitlines(keepends=True)
            if not had_mcp:
                separator = "" if source.endswith(("\n", "\r")) else newline
                return source + separator + render_yaml_fragment(
                    CommentedMap({"mcp": CommentedMap({"servers": servers})}), newline
                )
            if not had_servers:
                fragment = render_yaml_fragment(
                    CommentedMap({"mcp": CommentedMap({"servers": servers})}), newline
                )
                addition = "".join(fragment.splitlines(keepends=True)[1:])
                start = data.lc.key("mcp")[0]
                original = lines[start].rstrip("\r\n")
                if not re.match(r"^mcp:\s*(?:#.*)?$", original):
                    comment = original.partition("#")[2]
                    header = "mcp:" + (" #" + comment if comment else "") + newline
                    return "".join(lines[:start]) + header + addition + "".join(lines[start + 1:])
                insert_at = yaml_block_end(lines, start, 0)
                separator = newline if insert_at and not lines[insert_at - 1].endswith("\n") else ""
                return "".join(lines[:insert_at]) + separator + addition + "".join(lines[insert_at:])
            if len(servers) == 1:
                header = data["mcp"].lc.key("servers")[0]
                original = lines[header].rstrip("\r\n")
                comment = original.partition("#")[2]
                replacement = "  servers:" + (" #" + comment if comment else "") + newline
                replacement += _render_server(name, saved, newline)
                return "".join(lines[:header]) + replacement + "".join(lines[header + 1:])

            previous = list(servers)[-2]
            start = servers.lc.key(previous)[0]
            insert_at = yaml_block_end(lines, start, 4)
            separator = newline if insert_at and not lines[insert_at - 1].endswith("\n") else ""
            return (
                "".join(lines[:insert_at])
                + separator
                + _render_server(name, saved, newline)
                + "".join(lines[insert_at:])
            )

        _edit_config(add_server)
        assert saved is not None
        return _server_info(name, saved)


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
        saved: CommentedMap | None = None

        # 只替换目标服务器配置块
        def change_server(
            source: str,
            data: CommentedMap,
            servers: CommentedMap,
            had_mcp: bool,
            had_servers: bool,
        ) -> str:
            nonlocal saved
            target = servers.get(name)
            if target is None:
                raise MCPConfigManagementError(404, f"MCP 服务器不存在：{name}")
            lines = source.splitlines(keepends=True)
            start = servers.lc.key(name)[0]
            end = yaml_block_end(lines, start, 4)
            _merge_server(target, changes)
            saved = target
            newline = "\r\n" if "\r\n" in source else "\n"
            replacement = _render_server(name, target, newline)
            original = lines[start]
            if re.match(r"^\s*[^:]+:\s*(?:#.*)?$", original):
                replacement = original + "".join(replacement.splitlines(keepends=True)[1:])
            return "".join(lines[:start]) + replacement + "".join(lines[end:])

        _edit_config(change_server)
        assert saved is not None
        return _server_info(name, saved)


# 删除服务器
def delete_mcp_server(name: str) -> None:
    with _write_lock:
        # 只移除目标服务器配置块
        def remove_server(
            source: str,
            data: CommentedMap,
            servers: CommentedMap,
            had_mcp: bool,
            had_servers: bool,
        ) -> str:
            if name not in servers:
                raise MCPConfigManagementError(404, f"MCP 服务器不存在：{name}")
            lines = source.splitlines(keepends=True)
            start = servers.lc.key(name)[0]
            end = yaml_block_end(lines, start, 4)
            del servers[name]
            if servers:
                return "".join(lines[:start] + lines[end:])
            servers.fa.set_flow_style()
            header = data["mcp"].lc.key("servers")[0]
            original = lines[header].rstrip("\r\n")
            comment = original.partition("#")[2]
            newline = "\r\n" if "\r\n" in source else "\n"
            replacement = "  servers: {}" + (" #" + comment if comment else "") + newline
            return "".join(lines[:header]) + replacement + "".join(lines[header + 1:start] + lines[end:])

        _edit_config(remove_server)
