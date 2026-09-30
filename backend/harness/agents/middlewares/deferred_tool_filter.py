# 懒加载工具可见性中间件

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

from harness.tools.tool_search import registry_entries


# 从模型可见集剔除懒加载工具，不动注册表
class DeferredToolFilterMiddleware(AgentMiddleware):
    # 剔除懒加载工具，无变化时原样返回
    @staticmethod
    def _filter(request: ModelRequest) -> ModelRequest:
        deferred = {entry.name for entry in registry_entries()}
        if not deferred:
            return request

        visible = [
            item
            for item in request.tools
            if getattr(item, "name", None) not in deferred
        ]
        if len(visible) == len(request.tools):
            return request

        return request.override(tools=visible)

    # 包装同步模型调用
    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        return handler(self._filter(request))

    # 包装异步模型调用
    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        return await handler(self._filter(request))
