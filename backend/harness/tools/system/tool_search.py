# 懒加载工具查找

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool
from langchain_core.utils.function_calling import convert_to_openai_function
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field

from harness.core.logger import get_logger
from harness.tools.loader import enabled_items, import_tool
from harness.tools.tool_settings import get_tool_settings


logger = get_logger(__name__)


# 懒加载工具条目
@dataclass(frozen=True)
class ToolEntry:
    # 工具名
    name: str
    # 所属工具组
    group: str
    # 检索别名
    aliases: tuple[str, ...]
    # 工具说明
    description: str
    # 已导入的工具对象
    tool: BaseTool


# 工具目录
_entries: list[ToolEntry] = []


# 归一化工具组名称
def _normalize(text: str) -> str:
    return text.strip().casefold()


# 工具目录构建
def build_registry() -> list[BaseTool]:
    entries: list[ToolEntry] = []
    for item in enabled_items(False):
        try:
            imported = import_tool(item.get("use"))
        except (ImportError, ValueError) as error:
            logger.warning("懒加载工具导入失败，跳过", tool=str(item.get("name")), error=str(error))
            continue

        # 别名列表
        raw_aliases = item.get("aliases")
        aliases: tuple[str, ...] = ()
        if isinstance(raw_aliases, (list, tuple)):
            aliases = tuple(text for text in (str(alias).strip() for alias in raw_aliases) if text)

        entries.append(
            ToolEntry(
                name=imported.name,
                group=str(item.get("group") or ""),
                aliases=aliases,
                description=str(item.get("description") or "") or (imported.description or ""),
                tool=imported,
            )
        )

    global _entries
    _entries = entries
    return [entry.tool for entry in entries]


# 当前目录条目
def registry_entries() -> list[ToolEntry]:
    return list(_entries)


# 工具目录指纹
def catalog_hash(entries: Sequence[ToolEntry] | None = None) -> str:
    source = _entries if entries is None else entries
    definitions = [
        {"name": entry.name, "schema": convert_to_openai_function(entry.tool)}
        for entry in sorted(source, key=lambda item: item.name)
    ]
    serialized = json.dumps(definitions, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


# 懒加载工具名单
def deferred_tools_section() -> str:
    names = [entry.name for entry in _entries]
    if not names:
        return ""

    listing = "\n".join(f"- {name}" for name in names)
    return (
        "\n\n以下工具尚未绑定给模型，需要时先调用 tool_search 取回参数定义，取到后本轮即可调用：\n"
        f"{listing}"
    )


# 正则编译
def _compile_query(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        return re.compile(re.escape(pattern), re.IGNORECASE)


# 可检索文本
def _searchable_text(entry: ToolEntry) -> str:
    return " ".join((entry.name, entry.description, *entry.aliases))


# 工具目录检索
def _search(
    query: str,
    limit: int,
    group: str | None = None,
    *,
    entries: Sequence[ToolEntry] | None = None,
) -> list[ToolEntry]:
    if limit <= 0:
        raise ValueError(f"返回条数上限必须为正数：{limit}")

    target = query.strip()
    if not target:
        return []

    entries = [
        entry
        for entry in (_entries if entries is None else entries)
        if not group or _normalize(entry.group) == _normalize(group)
    ]

    # 精确名称匹配
    if target.startswith("select:"):
        wanted = {name.strip() for name in target[7:].split(",")}
        return [entry for entry in entries if entry.name in wanted]

    # 名称限定与相关度排序
    if target.startswith("+"):
        parts = target[1:].split(None, 1)
        if not parts:
            return []
        required = parts[0].lower()
        matches = [entry for entry in entries if required in entry.name.lower()]
        if len(parts) > 1:
            regex = _compile_query(parts[1])
            matches.sort(key=lambda entry: len(regex.findall(_searchable_text(entry))), reverse=True)
        return matches[:limit]

    # 正则关键词匹配
    regex = _compile_query(target)
    scored = [
        (2 if regex.search(entry.name) else 1, entry)
        for entry in entries
        if regex.search(_searchable_text(entry))
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in scored[:limit]]


# 工具查找参数
class ToolSearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 检索词
    query: str = Field(
        description="查询：select:工具名1,工具名2 精确选择；+名称关键词 说明关键词 限定名称并排序；其他内容按名称、说明和别名做不区分大小写的正则匹配",
    )

    # 工具调用标识
    tool_call_id: Annotated[str, InjectedToolCallId]

    # 限定工具组
    group: str | None = Field(
        default=None,
        description="限定工具组，只在该组内检索；未提供时全目录检索",
    )


# 懒加载工具查找
@tool("tool_search", args_schema=ToolSearchArgs)
def tool_search(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    group: str | None = None,
) -> Command:
    """查找未绑定给模型的懒加载工具，取回其完整参数定义。

    已绑定的工具满足不了需求时使用。select: 可按准确工具名一次取回多个定义；
    + 开头时先按名称关键词筛选，再用剩余内容排序；其他查询匹配名称、说明和别名。
    普通查询支持不区分大小写的正则表达式，无效正则按普通文字匹配。
    命中的定义带参数 JSON Schema，取到后本轮即可直接调用该工具，不必重复查找。
    没有命中时返回空数组；配置中的上限无效时工具报错，错误原因随工具结果返回。

    Args:
        query: 查询：select:工具名1,工具名2 精确选择；+名称关键词 说明关键词 限定名称并排序；其他内容按名称、说明和别名做不区分大小写的正则匹配。
        group: 限定工具组，只在该组内检索；未提供时全目录检索。

    Returns:
        JSON 数组字符串，每个元素是一个命中工具的完整定义，含三个字段：
        - name: 工具名，调用该工具时用的名字
        - description: 工具说明与用法
        - parameters: 参数的 JSON Schema，决定调用时允许哪些字段
    """
    # 返回上限配置
    limit = get_tool_settings("tool_search").get("default_max_results")
    if limit is None:
        raise ValueError("tool_search 未配置返回上限：settings.default_max_results 缺失")

    snapshot = tuple(_entries)
    entries = _search(query, int(limit), group, entries=snapshot)
    content = json.dumps(
        [convert_to_openai_function(entry.tool) for entry in entries], ensure_ascii=False
    )
    # 开放工具与检索结果
    return Command(
        update={
            "promoted": {"catalog_hash": catalog_hash(snapshot), "names": [entry.name for entry in entries]},
            "messages": [ToolMessage(content=content, name="tool_search", tool_call_id=tool_call_id)],
        }
    )
