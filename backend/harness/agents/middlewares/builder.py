# Agent 中间件装配

from collections.abc import Sequence

from langchain.agents.middleware import AgentMiddleware

from harness.agents.middlewares.tool_call import ToolCallMiddleware


# 装配默认中间件和外部中间件
def build_agent_middleware(
    middleware: Sequence[AgentMiddleware] | None = None,
) -> list[AgentMiddleware]:
    items = list(middleware or ())
    if any(isinstance(item, ToolCallMiddleware) for item in items):
        return items

    return [
        ToolCallMiddleware(),
        *items
    ]
