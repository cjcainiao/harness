# MCP 工具命名与目录条目

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence

from harness.mcp.loader import MCPServerDiscovery
from harness.tools.system.tool_search import ToolEntry


# 模型工具名的长度上限
_TOOL_NAME_LIMIT = 64


# 工具名称归一化
def _name_part(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    if normalized:
        return normalized
    return f"tool_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:8]}"


# 服务器前缀命名
def mcp_tool_name(server_name: str, tool_name: str) -> str:
    name = f"{_name_part(server_name)}_{_name_part(tool_name)}"
    if len(name) <= _TOOL_NAME_LIMIT:
        return name
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    return f"{name[:_TOOL_NAME_LIMIT - len(digest) - 1]}_{digest}"


# MCP 工具目录构建
def build_mcp_entries(
    discoveries: Mapping[str, MCPServerDiscovery],
    *,
    reserved_names: Sequence[str] = (),
) -> tuple[ToolEntry, ...]:
    origins = {name: "现有工具" for name in reserved_names}
    entries: list[ToolEntry] = []

    for server_name, discovery in discoveries.items():
        if discovery.status.state != "connected":
            continue
        for original in discovery.tools:
            name = mcp_tool_name(server_name, original.name)
            origin = f"{server_name}/{original.name}"
            if name in origins:
                raise ValueError(f"MCP 工具名称冲突：{name}（{origins[name]} 与 {origin}）")
            origins[name] = origin

            # 原工具定义保留
            renamed = original.model_copy(update={"name": name})
            entries.append(
                ToolEntry(
                    name=name,
                    group="mcp",
                    aliases=(server_name, original.name),
                    description=original.description or "",
                    tool=renamed,
                )
            )

    return tuple(entries)
