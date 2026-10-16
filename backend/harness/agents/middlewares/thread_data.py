# 会话工作空间中间件

from __future__ import annotations

from typing import override

from langchain.agents.middleware import AgentMiddleware
from langgraph.config import get_config
from langgraph.runtime import Runtime

from harness.agents.thread_state import ThreadState
from harness.sandbox.paths import workspace_path_for


# 每轮运行前写入会话工作空间路径
class ThreadDataMiddleware(AgentMiddleware[ThreadState]):
    state_schema = ThreadState

    @override
    def before_agent(self, state: ThreadState, runtime: Runtime) -> dict[str, str]:
        context = runtime.context or {}
        thread_id = context.get("thread_id") or get_config().get("configurable", {}).get("thread_id")
        if not isinstance(thread_id, str) or not thread_id:
            raise ValueError("缺少 thread_id，无法确定会话工作空间")

        return {"workspace_path": str(workspace_path_for(thread_id))}
