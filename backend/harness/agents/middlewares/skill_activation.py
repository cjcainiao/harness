# 显式技能激活中间件

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse


# 模型调用前处理显式技能
class SkillActivationMiddleware(AgentMiddleware):
    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        raise NotImplementedError("显式技能激活尚未实现")

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        raise NotImplementedError("显式技能激活尚未实现")
