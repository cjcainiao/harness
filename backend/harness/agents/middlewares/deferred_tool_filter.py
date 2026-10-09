# 懒加载工具可见性中间件

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, override

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command


# 懒加载工具可见性与执行控制
class DeferredToolFilterMiddleware(AgentMiddleware):
    def __init__(self, deferred_names: frozenset[str], catalog_hash: str):
        super().__init__()
        self._deferred = deferred_names
        self._catalog_hash = catalog_hash

    # 当前目录已开放工具
    def _promoted(self, state: Mapping[str, Any] | None) -> set[str]:
        promoted = (state or {}).get("promoted")
        if not isinstance(promoted, Mapping) or promoted.get("catalog_hash") != self._catalog_hash:
            return set()
        names = promoted.get("names")
        if not isinstance(names, list):
            return set()
        return {name for name in names if isinstance(name, str)}

    def _hidden(self, state: Mapping[str, Any] | None) -> set[str]:
        return set(self._deferred) - self._promoted(state)

    # 模型可见工具过滤
    def _filter(self, request: ModelRequest) -> ModelRequest:
        hidden = self._hidden(request.state)
        if not hidden:
            return request

        visible = [
            item
            for item in request.tools
            if getattr(item, "name", None) not in hidden
        ]
        if len(visible) == len(request.tools):
            return request

        return request.override(tools=visible)

    # 未开放工具拦截
    def _blocked_tool_message(self, request: ToolCallRequest) -> ToolMessage | None:
        name = str(request.tool_call.get("name") or "")
        if name not in self._hidden(request.state):
            return None
        return ToolMessage(
            content=f"工具 {name} 尚未开放，请先调用 tool_search 获取参数定义后重试。",
            name=name,
            tool_call_id=str(request.tool_call.get("id") or "missing_tool_call_id"),
            status="error",
        )

    # 包装同步模型调用
    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        return handler(self._filter(request))

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        blocked = self._blocked_tool_message(request)
        return blocked if blocked is not None else handler(request)

    # 包装异步模型调用
    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        return await handler(self._filter(request))

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        blocked = self._blocked_tool_message(request)
        return blocked if blocked is not None else await handler(request)
