# 工具加载器

from __future__ import annotations

import importlib
from typing import Any

from langchain_core.tools import BaseTool

from harness.config.app_config import get_app_config


# 默认工具所属组，其余组走懒加载
DEFAULT_GROUP = "system"


# 按 use 取工具对象
def import_tool(use: Any) -> BaseTool:
    module_path, separator, attr_name = str(use).partition(":")
    if not separator or not module_path or not attr_name:
        raise ValueError(f"工具实现路径格式错误：{use}")
    try:
        module = importlib.import_module(module_path)
    except ImportError as error:
        raise ImportError(f"无法导入工具模块：{module_path}") from error

    # 工具须是 BaseTool 实例
    tool = getattr(module, attr_name, None)
    if not isinstance(tool, BaseTool):
        raise ValueError(f"工具必须是 BaseTool 实例：{use}")
    return tool


# 取已启用注册项，按是否默认组筛选
def enabled_items(is_default: bool) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in get_app_config().tools:
        if not item.get("enabled"):
            continue
        if (item.get("group") == DEFAULT_GROUP) != is_default:
            continue
        items.append(item)
    return items


# 加载默认工具
def load_default_tools() -> list[BaseTool]:
    return [import_tool(item.get("use")) for item in enabled_items(True)]
