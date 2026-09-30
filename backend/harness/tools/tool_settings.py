# 工具配置查找

from __future__ import annotations

from typing import Any

from harness.config.app_config import get_app_config


# 按工具名读取其在 config.yaml 中的 settings
def get_tool_settings(name: str) -> dict[str, Any]:
    for item in get_app_config().tools:
        if item.get("name") == name:
            settings = item.get("settings")
            return settings if isinstance(settings, dict) else {}
    return {}
