# MCP 服务器配置业务

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from app.schemas.config.mcp_schema import (
    MCPServerConfigInfo,
    MCPServerStatusInfo,
    MCPStatusInfo,
)
from harness.config.app_config import AppConfig, get_app_config, reload_app_config
from harness.config.mcp_config import MCPConfig, MCPServerConfig
from harness.mcp.cache import (
    MCPStatusSnapshot,
    get_mcp_status,
    refresh_mcp_discoveries,
    reset_mcp_cache,
)
from harness.mcp.tools import mcp_tool_name
from harness.utils.yaml_util import edit_yaml_text, load_yaml, render_yaml_fragment, yaml_block_end


_secret_name = re.compile(
    r"(?:authorization|api[_-]?key|access[_-]?key|token|secret|password|credential|auth|^key$)",
    re.I,
)
_env_reference = re.compile(r"\$(?:\{[A-Za-z_][A-Za-z0-9_]*\}|[A-Za-z_][A-Za-z0-9_]*)")


# 隐藏地址中的凭据与查询参数
def _visible_url(value: Any) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    if not isinstance(value, str) or value.startswith("$"):
        return None, True

    try:
        parsed = urlsplit(value)
        if parsed.username or parsed.password or "$" in parsed.netloc or "$" in parsed.path:
            return None, True
        visible = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    except ValueError:
        return None, True
    return visible, bool(parsed.query or parsed.fragment)


# 读取不含连接凭据的服务器列表
def list_mcp_server_configs() -> list[MCPServerConfigInfo]:
    config = get_app_config().mcp
    data = load_yaml(AppConfig.resolve_config_path())
    if not isinstance(data, dict):
        raise ValueError("MCP 配置格式无效")
    mcp = data.get("mcp") or {}
    if not isinstance(mcp, dict):
        raise ValueError("MCP 配置格式无效")
    servers = mcp.get("servers") or {}
    if not isinstance(servers, dict):
        raise ValueError("MCP 服务器列表格式无效")

    result: list[MCPServerConfigInfo] = []
    for name, server in config.servers.items():
        raw = servers.get(name)
        if not isinstance(raw, dict):
            raise ValueError("MCP 服务器配置格式无效")
        url, has_hidden_url = _visible_url(raw.get("url"))
        result.append(
            MCPServerConfigInfo(
                name=name,
                description=raw.get("description"),
                enabled=server.enabled,
                transport=server.transport,
                url=url,
                has_hidden_url=has_hidden_url,
                header_names=list((raw.get("headers") or {}).keys()),
                command_configured=bool(raw.get("command")),
                args_count=len(raw.get("args") or []),
                env_names=list((raw.get("env") or {}).keys()),
                cwd_configured=bool(raw.get("cwd")),
                connect_timeout_seconds=server.connect_timeout_seconds,
                call_timeout_seconds=server.call_timeout_seconds,
            )
        )
    return result


# 定位并修改服务器启停字段
def _edit_server_enabled(source: str, name: str, enabled: bool) -> str:
    data = YAML().load(source)
    mcp = data.get("mcp") if isinstance(data, CommentedMap) else None
    servers = mcp.get("servers") if isinstance(mcp, CommentedMap) else None
    server = servers.get(name) if isinstance(servers, CommentedMap) else None
    if server is None:
        raise LookupError("MCP 服务器不存在")
    if not isinstance(server, CommentedMap):
        raise ValueError("MCP 服务器配置格式无效")
    if server.get("enabled", False) is enabled:
        return source

    lines = source.splitlines(keepends=True)
    value = str(enabled).lower()
    if "enabled" in server:
        line_index, column = server.lc.value("enabled")
        line = lines[line_index]
        match = re.match(r"(?i:true|false)\b", line[column:])
        if match is None:
            raise ValueError("MCP 服务器启停字段格式无效")
        lines[line_index] = line[:column] + value + line[column + match.end() :]
    else:
        server_line, _ = servers.lc.key(name)
        if not server:
            raise ValueError("MCP 服务器配置格式无效")
        first_line, indent = server.lc.key(next(iter(server)))
        if first_line <= server_line:
            raise ValueError("MCP 服务器配置格式暂不支持行内写法")
        newline = "\r\n" if lines[server_line].endswith("\r\n") else "\n"
        lines.insert(server_line + 1, " " * indent + f"enabled: {value}" + newline)

    updated = "".join(lines)
    candidate = YAML(typ="safe").load(updated)
    try:
        mcp_data = candidate.get("mcp") if isinstance(candidate, dict) else None
        resolved = AppConfig.resolve_mcp_env_variables(mcp_data)
        MCPConfig.model_validate(resolved)
    except (ValidationError, ValueError, TypeError) as error:
        raise ValueError("MCP 配置无效或引用的环境变量不可用") from error
    return updated


# 保存服务器启停状态
def set_mcp_server_enabled(name: str, enabled: bool) -> MCPServerConfigInfo:
    changed = False

    def edit(source: str) -> str:
        nonlocal changed
        updated = _edit_server_enabled(source, name, enabled)
        changed = updated != source
        return updated

    edit_yaml_text(AppConfig.resolve_config_path(), edit)
    if changed:
        reload_app_config()
        reset_mcp_cache()
    return next(server for server in list_mcp_server_configs() if server.name == name)


# 校验新增凭据使用环境变量引用
def _check_secret_values(values: dict[str, str | None] | None) -> None:
    if values is None:
        return
    for key, value in values.items():
        if value is not None and _secret_name.search(key) and not _env_reference.search(value):
            raise ValueError("敏感配置必须引用环境变量")


# 校验服务器地址不直接包含凭据
def _check_url_secret(value: str | None) -> None:
    if value is None or value.startswith("$"):
        return
    try:
        parsed = urlsplit(value)
        if parsed.username or parsed.password:
            raise ValueError("MCP 地址不能直接包含用户名或密码")
        for key, item in parse_qsl(parsed.query, keep_blank_values=True):
            _check_secret_values({key: item})
    except ValueError as error:
        raise ValueError("MCP 地址不能直接包含凭据") from error


# 在指定位置插入配置块
def _insert_yaml_fragment(lines: list[str], position: int, fragment: str, newline: str) -> str:
    prefix = "".join(lines[:position])
    if prefix and not prefix.endswith("\n"):
        prefix += newline
    return prefix + fragment + "".join(lines[position:])


# 将空配置行改为块结构
def _expand_empty_mapping_header(line: str, key: str, newline: str) -> str:
    content = line.rstrip("\r\n")
    match = re.fullmatch(
        rf'''(\s*(?:{key}|'{key}'|"{key}")\s*:)[ \t]*(?:\{{\}}|null|~)?([ \t]*(?:#.*)?)''',
        content,
    )
    if match is None:
        raise ValueError("MCP 配置格式暂不支持行内写法")
    suffix = match.group(2)
    if suffix.startswith("#"):
        suffix = " " + suffix
    return match.group(1) + suffix + newline


# 插入新服务器的 YAML 文本
def _insert_server_yaml(source: str, name: str, values: dict[str, Any]) -> str:
    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(source)
    if data is None:
        data = CommentedMap()
    if not isinstance(data, CommentedMap):
        raise ValueError("配置文件根节点必须是键值结构")

    mcp_exists = "mcp" in data
    mcp = data.get("mcp")
    if mcp is None:
        mcp = CommentedMap()
        data["mcp"] = mcp
    if not isinstance(mcp, CommentedMap):
        raise ValueError("MCP 配置格式无效")

    servers_exists = "servers" in mcp
    servers = mcp.get("servers")
    if servers is None:
        servers = CommentedMap()
        mcp["servers"] = servers
    if not isinstance(servers, CommentedMap):
        raise ValueError("MCP 服务器列表格式无效")
    if name in servers:
        raise FileExistsError("MCP 服务器名称重复")

    _check_secret_values(values.get("headers"))
    _check_secret_values(values.get("env"))
    _check_url_secret(values.get("url"))
    servers[name] = CommentedMap(values)
    try:
        resolved = AppConfig.resolve_mcp_env_variables(mcp)
        MCPConfig.model_validate(resolved)
    except (ValidationError, ValueError, TypeError) as error:
        raise ValueError("MCP 配置无效或引用的环境变量不可用") from error

    newline = "\r\n" if "\r\n" in source else "\n"
    lines = source.splitlines(keepends=True)
    wrapper = CommentedMap({"mcp": CommentedMap({"servers": CommentedMap({name: CommentedMap(values)})})})
    fragment_lines = render_yaml_fragment(wrapper, newline).splitlines(keepends=True)

    if not mcp_exists:
        updated = _insert_yaml_fragment(lines, len(lines), "".join(fragment_lines), newline)
    else:
        mcp_line, mcp_indent = data.lc.key("mcp")
        if not servers_exists:
            child_indent = mcp_indent + 2
            existing_keys = [key for key in mcp if key != "servers"]
            if existing_keys:
                child_indent = mcp.lc.key(existing_keys[0])[1]
                if child_indent <= mcp_indent:
                    raise ValueError("MCP 配置格式暂不支持行内写法")
            fragment = _shift_fragment_indent("".join(fragment_lines[1:]), child_indent - 2)
            if not existing_keys:
                lines[mcp_line] = _expand_empty_mapping_header(lines[mcp_line], "mcp", newline)
                position = mcp_line + 1
            else:
                position = yaml_block_end(lines, mcp_line, mcp_indent)
            updated = _insert_yaml_fragment(lines, position, fragment, newline)
        else:
            server_header, server_indent = mcp.lc.key("servers")
            if server_indent <= mcp_indent:
                raise ValueError("MCP 服务器列表缩进格式无效")
            if len(servers) == 1:
                lines[server_header] = _expand_empty_mapping_header(lines[server_header], "servers", newline)
                position = server_header + 1
                name_indent = server_indent + (server_indent - mcp_indent)
            else:
                previous = list(servers)[-2]
                position_info = servers.lc.key(previous)
                if position_info is None:
                    raise ValueError("MCP 服务器列表格式暂不支持合并键")
                previous_line, name_indent = position_info
                if previous_line <= server_header or name_indent <= server_indent:
                    raise ValueError("MCP 服务器列表格式暂不支持行内写法")
                position = yaml_block_end(lines, previous_line, name_indent)
            fragment = _shift_fragment_indent("".join(fragment_lines[2:]), name_indent - 4)
            updated = _insert_yaml_fragment(lines, position, fragment, newline)

    if YAML(typ="safe").load(updated) != data:
        raise ValueError("新增 MCP 服务器后的配置校验失败")
    return updated


# 保存新增服务器配置
def create_mcp_server(name: str, values: dict[str, Any]) -> MCPServerConfigInfo:
    edit_yaml_text(
        AppConfig.resolve_config_path(),
        lambda source: _insert_server_yaml(source, name, values),
    )
    reload_app_config()
    reset_mcp_cache()
    return next(server for server in list_mcp_server_configs() if server.name == name)


# 合并普通字段和请求头、环境变量
def _merge_server_changes(server: CommentedMap, changes: dict[str, Any]) -> None:
    for field, value in changes.items():
        if field not in {"headers", "env"}:
            if value is None and field in {
                "enabled",
                "transport",
                "args",
                "connect_timeout_seconds",
                "call_timeout_seconds",
            }:
                raise ValueError("MCP 服务器字段不能设为空")
            if field == "url":
                _check_url_secret(value)
            server[field] = value
            continue

        _check_secret_values(value)
        if value is None:
            server[field] = CommentedMap()
            continue
        current = server.get(field)
        if not isinstance(current, CommentedMap):
            current = CommentedMap()
        for key, item in value.items():
            if item is None:
                current.pop(key, None)
            else:
                current[key] = item
        server[field] = current


# 对齐修改字段的原有缩进
def _shift_fragment_indent(fragment: str, offset: int) -> str:
    adjusted: list[str] = []
    for line in fragment.splitlines(keepends=True):
        if not line.strip():
            adjusted.append(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent + offset < 0:
            raise ValueError("MCP 服务器字段缩进格式无效")
        adjusted.append(" " * (indent + offset) + line[indent:])
    return "".join(adjusted)


# 修改指定字段的 YAML 文本
def _edit_server_patch(source: str, name: str, changes: dict[str, Any]) -> str:
    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(source)
    mcp = data.get("mcp") if isinstance(data, CommentedMap) else None
    servers = mcp.get("servers") if isinstance(mcp, CommentedMap) else None
    server = servers.get(name) if isinstance(servers, CommentedMap) else None
    if server is None:
        raise LookupError("MCP 服务器不存在")
    if not isinstance(server, CommentedMap):
        raise ValueError("MCP 服务器配置格式无效")

    position = servers.lc.key(name)
    if position is None:
        raise ValueError("MCP 服务器配置格式暂不支持合并键")
    start, indent = position
    if server and server.lc.key(next(iter(server)))[0] <= start:
        raise ValueError("MCP 服务器配置格式暂不支持行内写法")

    first_original_field = next(iter(server), None)
    original_keys = set(server)
    before = {
        field: deepcopy(
            server.get(field, MCPServerConfig.model_fields[field].get_default(call_default_factory=True))
        )
        for field in changes
    }
    _merge_server_changes(server, changes)
    changed_fields = [field for field in changes if before[field] != server[field]]
    for field in changes:
        if field not in original_keys and field not in changed_fields:
            server.pop(field, None)
    if not changed_fields:
        return source

    lines = source.splitlines(keepends=True)
    newline = "\r\n" if lines[start].endswith("\r\n") else "\n"
    new_field_indent = server.lc.key(first_original_field)[1] if first_original_field else indent + 2
    wrapper = CommentedMap({"mcp": CommentedMap({"servers": CommentedMap({name: server})})})
    rendered = render_yaml_fragment(wrapper, newline, mapping_indent=new_field_indent - indent)
    rendered_lines = rendered.splitlines(keepends=True)
    rendered_server = YAML().load(rendered)["mcp"]["servers"][name]

    patches: list[tuple[int, int, str]] = []
    additions: list[str] = []
    for field in changed_fields:
        rendered_start, rendered_indent = rendered_server.lc.key(field)
        rendered_end = yaml_block_end(rendered_lines, rendered_start, rendered_indent)
        fragment = "".join(rendered_lines[rendered_start:rendered_end])
        if field in original_keys:
            field_start, field_indent = server.lc.key(field)
            field_end = yaml_block_end(lines, field_start, field_indent)
            if field_indent != rendered_indent:
                fragment = _shift_fragment_indent(fragment, field_indent - rendered_indent)
            if field_end == len(lines) and not lines[-1].endswith("\n"):
                fragment = fragment.rstrip("\r\n")
            patches.append((field_start, field_end, fragment))
        else:
            additions.append(_shift_fragment_indent(fragment, new_field_indent - rendered_indent))

    if additions:
        insert_at = yaml_block_end(lines, start, indent)
        addition = "".join(additions)
        if insert_at and not lines[insert_at - 1].endswith("\n"):
            addition = newline + addition
        if insert_at == len(lines) and not source.endswith("\n"):
            addition = addition.rstrip("\r\n")
        patches.append((insert_at, insert_at, addition))

    for field_start, field_end, fragment in sorted(patches, key=lambda item: item[0], reverse=True):
        lines[field_start:field_end] = [fragment]
    updated = "".join(lines)
    if YAML().load(updated) != data:
        raise ValueError("修改 MCP 服务器后的配置校验失败")
    try:
        candidate = YAML(typ="safe").load(updated)
        mcp_data = AppConfig.resolve_mcp_env_variables(candidate["mcp"])
        MCPConfig.model_validate(mcp_data)
    except (ValidationError, ValueError, TypeError) as error:
        raise ValueError("MCP 配置无效或引用的环境变量不可用") from error
    return updated


# 保存服务器配置修改
def update_mcp_server(name: str, changes: dict[str, Any]) -> MCPServerConfigInfo:
    changed = False

    def edit(source: str) -> str:
        nonlocal changed
        updated = _edit_server_patch(source, name, changes)
        changed = updated != source
        return updated

    edit_yaml_text(AppConfig.resolve_config_path(), edit)
    if changed:
        reload_app_config()
        reset_mcp_cache()
    return next(server for server in list_mcp_server_configs() if server.name == name)


# 删除服务器配置块
def _remove_server_yaml(source: str, name: str) -> str:
    data = YAML().load(source)
    mcp = data.get("mcp") if isinstance(data, CommentedMap) else None
    servers = mcp.get("servers") if isinstance(mcp, CommentedMap) else None
    if not isinstance(servers, CommentedMap):
        raise LookupError("MCP 服务器不存在")
    if name not in servers:
        raise LookupError("MCP 服务器不存在")

    lines = source.splitlines(keepends=True)
    header, header_indent = mcp.lc.key("servers")
    position = servers.lc.key(name)
    if position is None:
        raise ValueError("MCP 服务器配置格式暂不支持合并键")
    start, indent = position
    if start <= header or indent <= header_indent:
        raise ValueError("MCP 服务器列表格式暂不支持行内写法")
    end = yaml_block_end(lines, start, indent)
    if len(servers) == 1:
        header_line = lines[header]
        content = header_line.rstrip("\r\n")
        newline = header_line[len(content) :]
        match = re.fullmatch(r'''(\s*(?:servers|'servers'|"servers")\s*:)([ \t]*)(#.*)?''', content)
        if match is None:
            raise ValueError("MCP 服务器列表格式暂不支持行内写法")
        comment = match.group(3) or ""
        spacing = match.group(2) if comment else ""
        lines[header] = f"{match.group(1)} {{}}{spacing}{comment}{newline}"

    updated = "".join(lines[:start] + lines[end:])
    expected = YAML(typ="safe").load(source)
    expected["mcp"]["servers"].pop(name)
    if YAML(typ="safe").load(updated) != expected:
        raise ValueError("删除 MCP 服务器后的配置校验失败")
    return updated


# 删除服务器并刷新配置
def delete_mcp_server(name: str) -> None:
    edit_yaml_text(
        AppConfig.resolve_config_path(),
        lambda source: _remove_server_yaml(source, name),
    )
    reload_app_config()
    reset_mcp_cache()


# 转换服务器发现状态
def _status_info(config: MCPConfig, snapshot: MCPStatusSnapshot) -> MCPStatusInfo:
    servers = [
        MCPServerStatusInfo(
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


# 读取缓存中的服务器发现状态
def read_mcp_status() -> MCPStatusInfo:
    config = get_app_config().mcp
    return _status_info(config, get_mcp_status(config))


# 刷新服务器工具发现状态
async def refresh_mcp_status() -> MCPStatusInfo:
    config = get_app_config().mcp
    snapshot = await refresh_mcp_discoveries(config)
    return _status_info(config, snapshot)
