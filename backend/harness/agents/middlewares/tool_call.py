# 工具调用事件中间件

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.errors import GraphBubbleUp
from langgraph.types import Command

from harness.core.logger import get_logger


logger = get_logger(__name__)
ToolResult = ToolMessage | Command[Any]


class ToolCallMiddleware(AgentMiddleware):
    # 发送工具执行事件
    @staticmethod
    def _emit(request: ToolCallRequest, payload: dict[str, Any]) -> None:
        request.runtime.stream_writer(payload)

    # 组装工具标识
    @staticmethod
    def _identity(request: ToolCallRequest) -> dict[str, Any]:
        return {
            "tool": request.tool_call["name"],
            "tool_call_id": request.tool_call["id"],
        }

    # 发送工具开始事件
    def _emit_start(self, request: ToolCallRequest) -> None:
        self._emit(
            request,
            {
                "type": "tool_start",
                **self._identity(request),
                "arguments": request.tool_call["args"],
            },
        )

    # 发送工具完成事件
    def _emit_result(
        self, request: ToolCallRequest, result: ToolResult, started_at: float
    ) -> None:
        payload: dict[str, Any] = {
            **self._identity(request),
            "duration_ms": round((time.perf_counter() - started_at) * 1000),
        }
        if isinstance(result, ToolMessage):
            payload["type"] = "tool_error" if result.status == "error" else "tool_result"
            payload["content"] = result.content
        else:
            payload["type"] = "tool_result"
        self._emit(request, payload)

    # 发送工具异常事件
    def _emit_error(
        self, request: ToolCallRequest, error: Exception, started_at: float
    ) -> None:
        logger.error(
            "工具调用失败",
            **self._identity(request),
            error=str(error),
            exc_info=True,
        )
        self._emit(
            request,
            {
                "type": "tool_error",
                **self._identity(request),
                "duration_ms": round((time.perf_counter() - started_at) * 1000),
                "message": "工具调用失败",
            },
        )

    # 包装同步工具调用
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolResult],
    ) -> ToolResult:
        self._emit_start(request)
        started_at = time.perf_counter()
        try:
            result = handler(request)
        except GraphBubbleUp:
            raise
        except Exception as error:
            self._emit_error(request, error, started_at)
            raise
        self._emit_result(request, result, started_at)
        return result

    # 包装异步工具调用
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolResult]],
    ) -> ToolResult:
        self._emit_start(request)
        started_at = time.perf_counter()
        try:
            result = await handler(request)
        except GraphBubbleUp:
            raise
        except Exception as error:
            self._emit_error(request, error, started_at)
            raise
        self._emit_result(request, result, started_at)
        return result
