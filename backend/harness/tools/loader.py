# 工具加载器

from __future__ import annotations

import importlib

from langchain_core.tools import BaseTool

from harness.config.app_config import get_app_config


# 加载默认工具
def load_default_tools() -> list[BaseTool]:
    tools: list[BaseTool] = []
    for item in get_app_config().tools:
        # 只取 system 组中已启用的工具
        if item.get("group") != "system" or not item.get("enabled"):
            continue

        # 按 module:attr 取工具对象
        use = item.get("use")
        module_path, separator, attr_name = str(use).partition(":")
        if not separator or not module_path or not attr_name:
            raise ValueError(f"工具实现路径格式错误：{use}")
        try:
            module = importlib.import_module(module_path)
        except ImportError as error:
            raise ImportError(f"无法导入工具模块：{module_path}") from error

        # 工具须是 BaseTool 实例，@tool 装饰后的成品
        tool = getattr(module, attr_name, None)
        if not isinstance(tool, BaseTool):
            raise ValueError(f"工具必须是 BaseTool 实例：{use}")
        tools.append(tool)

    return tools


# 加载延迟工具
def load_deferred_tools() -> list[BaseTool]:
    tools: list[BaseTool] = []
    for item in get_app_config().tools:
        # 只取 system 组之外已启用的工具
        if item.get("group") == "system" or not item.get("enabled"):
            continue

        # 按 module:attr 取工具对象
        use = item.get("use")
        module_path, separator, attr_name = str(use).partition(":")
        if not separator or not module_path or not attr_name:
            raise ValueError(f"工具实现路径格式错误：{use}")
        try:
            module = importlib.import_module(module_path)
        except ImportError as error:
            raise ImportError(f"无法导入工具模块：{module_path}") from error

        # 工具须是 BaseTool 实例，@tool 装饰后的成品
        tool = getattr(module, attr_name, None)
        if not isinstance(tool, BaseTool):
            raise ValueError(f"工具必须是 BaseTool 实例：{use}")
        tools.append(tool)

    return tools
