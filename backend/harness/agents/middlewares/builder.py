# Agent 中间件装配

from collections.abc import Sequence

from langchain.agents.middleware import AgentMiddleware

from harness.agents.middlewares.deferred_tool_filter import DeferredToolFilterMiddleware
from harness.agents.middlewares.model_debug import ModelDebugMiddleware
from harness.agents.middlewares.thread_data import ThreadDataMiddleware
from harness.agents.middlewares.tool_call import ToolCallMiddleware
from harness.config.app_config import get_app_config


# 装配默认中间件和外部中间件
def build_agent_middleware(
    middleware: Sequence[AgentMiddleware] | None = None,
) -> list[AgentMiddleware]:
    config = get_app_config()
    items = list(middleware or ())

    # 每轮运行前写入会话工作空间路径
    if not any(isinstance(item, ThreadDataMiddleware) for item in items):
        items.insert(0, ThreadDataMiddleware())

    # 懒加载开启时过滤模型可见工具
    if config.tool_search.get("enabled") and not any(
        isinstance(item, DeferredToolFilterMiddleware) for item in items
    ):
        items.append(DeferredToolFilterMiddleware())

    # 调试开启时打印最终发给模型的请求与响应，排在过滤之后才能看到真实可见集
    if config.system.debug and not any(
        isinstance(item, ModelDebugMiddleware) for item in items
    ):
        items.append(ModelDebugMiddleware())

    if any(isinstance(item, ToolCallMiddleware) for item in items):
        return items

    return [
        ToolCallMiddleware(),
        *items
    ]
