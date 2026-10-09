# 附件处理中间件

from __future__ import annotations

from typing import override

from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

from harness.agents.thread_state import ThreadState


class AttachmentMiddleware(AgentMiddleware[ThreadState]):
    state_schema = ThreadState

    # 附件处理入口
    @override
    def before_agent(self, state: ThreadState, runtime: Runtime) -> None:
        pass
