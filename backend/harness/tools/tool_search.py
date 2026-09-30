# 工具查找：懒加载工具目录与检索工具

from __future__ import annotations

import json
from dataclasses import dataclass

from langchain_core.tools import BaseTool, tool
from langchain_core.utils.function_calling import convert_to_openai_function
from pydantic import BaseModel, ConfigDict, Field

from harness.config.app_config import get_app_config
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
    # 工具说明，注册项未写时取工具自带描述
    description: str
    # 已导入的工具对象
    tool: BaseTool


# 目录条目，建图时整体替换
_entries: list[ToolEntry] = []


# 归一化匹配文本
def _normalize(text: str) -> str:
    return text.strip().casefold()


# 导入全部懒加载工具并建立目录
def build_registry() -> list[BaseTool]:
    entries: list[ToolEntry] = []
    for item in enabled_items(False):
        try:
            imported = import_tool(item.get("use"))
        except (ImportError, ValueError) as error:
            logger.warning("懒加载工具导入失败，跳过", tool=str(item.get("name")), error=str(error))
            continue

        # 别名只认列表，其余按无别名处理
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


# 懒加载工具名单段，提示模型先查参数定义
def deferred_tools_section() -> str:
    names = [entry.name for entry in _entries]
    if not names:
        return ""

    listing = "\n".join(f"- {name}" for name in names)
    return (
        "\n\n以下工具尚未绑定给模型，需要时先调用 tool_search 取回参数定义，取到后本轮即可调用：\n"
        f"{listing}"
    )


# 条目匹配分值，0 为不命中
def _score(entry: ToolEntry, query: str) -> int:
    target = _normalize(query)
    score = 0

    # 别名精确与互含
    for alias in entry.aliases:
        text = _normalize(alias)
        if not text:
            continue
        if text == target:
            score = max(score, 5)
        elif text in target or target in text:
            score = max(score, 4)

    # 工具名互含
    name = _normalize(entry.name)
    if name and name == target:
        score = max(score, 5)
    elif name and (name in target or target in name):
        score = max(score, 3)

    # 说明兜底
    if target in _normalize(entry.description):
        score = max(score, 1)

    return score


# 检索懒加载工具，分值从高到低取前 limit 条
def _search(query: str, limit: int, group: str | None = None) -> list[ToolEntry]:
    if not _normalize(query):
        raise ValueError("检索词不能为空")
    if limit <= 0:
        raise ValueError(f"返回条数上限必须为正数：{limit}")

    scored: list[tuple[int, str, ToolEntry]] = []
    for entry in _entries:
        # 限定工具组
        if group and _normalize(entry.group) != _normalize(group):
            continue
        score = _score(entry, query)
        if score > 0:
            scored.append((score, entry.name, entry))

    # 同分按工具名稳定排序
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in scored[:limit]]


# 工具查找参数
class ToolSearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 检索词
    query: str = Field(
        min_length=1,
        description="检索词，用于匹配工具别名、名称和说明，例如 翻译、unit convert",
    )

    # 限定工具组
    group: str | None = Field(
        default=None,
        description="限定工具组，只在该组内检索；未提供时全目录检索",
    )

    # 返回条目上限，配置未取到时才用模型传值
    max_results: int | None = Field(
        default=None,
        gt=0,
        description="返回条目上限，工具配置 default_max_results 与全局 tool_search 段的 max_results 都未配置时生效",
    )


# 按关键词查找懒加载工具
@tool("tool_search", args_schema=ToolSearchArgs)
def tool_search(query: str, group: str | None = None, max_results: int | None = None) -> str:
    """查找未绑定给模型的懒加载工具，取回其完整参数定义。

    已绑定的工具满足不了需求时使用，按检索词在工具目录里匹配别名、名称和说明，返回命中工具的函数定义。
    定义里带参数 JSON Schema，取到后本轮即可直接调用该工具，不必重复查找。
    目录里没有命中时返回空数组；检索词为空或上限非正数时工具报错，错误原因随工具结果返回。

    Args:
        query: 检索词，用于匹配工具别名、名称和说明，例如 翻译、unit convert。
        group: 限定工具组，只在该组内检索；未提供时全目录检索。
        max_results: 返回条目上限，工具配置 default_max_results 与全局 tool_search 段的 max_results 都未配置时生效。

    Returns:
        JSON 数组字符串，每个元素是一个命中工具的完整定义，含三个字段：
        - name: 工具名，调用该工具时用的名字
        - description: 工具说明与用法
        - parameters: 参数的 JSON Schema，决定调用时允许哪些字段
    """
    # 生效上限：工具自身 settings > 全局 tool_search 段 > 模型传值
    candidates = (
        get_tool_settings("tool_search").get("default_max_results"),
        get_app_config().tool_search.get("max_results"),
        max_results,
    )
    for limit in candidates:
        if limit is not None:
            break
    else:
        raise ValueError(
            "tool_search 未配置返回上限：settings.default_max_results 与 tool_search.max_results 均缺失"
        )

    entries = _search(query, int(limit), group)

    return json.dumps(
        [convert_to_openai_function(entry.tool) for entry in entries],
        ensure_ascii=False,
    )
