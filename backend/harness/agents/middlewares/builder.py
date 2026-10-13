# 代理中间件装配

from collections.abc import Sequence

from langchain.agents.middleware import AgentMiddleware

from harness.agents.middlewares.attachments import AttachmentMiddleware
from harness.agents.middlewares.deferred_tool_filter import DeferredToolFilterMiddleware
from harness.agents.middlewares.model_debug import ModelDebugMiddleware
from harness.agents.middlewares.skill_activation import SkillActivationMiddleware
from harness.agents.middlewares.thread_data import ThreadDataMiddleware
from harness.agents.middlewares.tool_call import ToolCallMiddleware
from harness.agents.middlewares.view_image import ViewImageMiddleware
from harness.config.app_config import AppConfig, get_app_config
from harness.tools.system.tool_search import ToolCatalog


# 组装代理中间件
def build_agent_middleware(
    middleware: Sequence[AgentMiddleware] | None = None,
    *,
    catalog: ToolCatalog | None = None,
    app_config: AppConfig | None = None,
) -> list[AgentMiddleware]:
    config = app_config or get_app_config()

    # 基础中间件
    items: list[AgentMiddleware] = [
        ToolCallMiddleware(),
        ThreadDataMiddleware(),
        AttachmentMiddleware(),
        SkillActivationMiddleware(),
        ViewImageMiddleware(),
    ]

    # 懒加载工具过滤
    if catalog is not None and catalog.entries:
        items.append(
            DeferredToolFilterMiddleware(
                frozenset(entry.name for entry in catalog.entries), catalog.fingerprint
            )
        )

    # 模型调用调试
    if config.system.debug:
        items.append(ModelDebugMiddleware())

    # 外部调试中间件
    items.extend(middleware or ())
    return items
