# 代理中间件装配

from collections.abc import Sequence

from langchain.agents.middleware import AgentMiddleware

from harness.agents.middlewares.attachments import AttachmentMiddleware
from harness.agents.middlewares.deferred_tool_filter import DeferredToolFilterMiddleware
from harness.agents.middlewares.model_debug import ModelDebugMiddleware
from harness.agents.middlewares.thread_data import ThreadDataMiddleware
from harness.agents.middlewares.tool_call import ToolCallMiddleware
from harness.agents.middlewares.view_image import ViewImageMiddleware
from harness.config.app_config import get_app_config
from harness.tools.system.tool_search import catalog_hash, registry_entries


# 组装代理中间件
def build_agent_middleware(
    middleware: Sequence[AgentMiddleware] | None = None,
) -> list[AgentMiddleware]:
    config = get_app_config()

    # 基础中间件
    items: list[AgentMiddleware] = [
        ToolCallMiddleware(),
        ThreadDataMiddleware(),
        AttachmentMiddleware(),
        ViewImageMiddleware(),
    ]

    # 工具查找配置
    search_enabled = any(
        item.get("name") == "tool_search" and item.get("group") == "system" and item.get("enabled")
        for item in config.tools
    )
    entries = registry_entries() if search_enabled else []
    # 懒加载工具过滤
    if entries:
        items.append(
            DeferredToolFilterMiddleware(
                frozenset(entry.name for entry in entries), catalog_hash(entries)
            )
        )

    # 模型调用调试
    if config.system.debug:
        items.append(ModelDebugMiddleware())

    # 外部调试中间件
    items.extend(middleware or ())
    return items
