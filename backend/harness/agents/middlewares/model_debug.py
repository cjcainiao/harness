# 模型调用调试中间件

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, override

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import message_to_dict
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_function

from harness.core.logger import get_logger


logger = get_logger(__name__)


# 转成日志字符串，避免结构化渲染遇到不支持的类型
def _dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


# 工具定义转成模型看到的函数声明
def _tool_payload(tool: BaseTool | dict[str, Any]) -> Any:
    return tool if isinstance(tool, dict) else convert_to_openai_function(tool)


# 打印每次调用模型的完整请求与响应
class ModelDebugMiddleware(AgentMiddleware):
    def __init__(self) -> None:
        super().__init__()
        # 本次图执行内的模型调用序号
        self.calls = 0

    # 打印发给模型的内容
    def _log_request(self, request: ModelRequest) -> int:
        self.calls += 1
        logger.info(
            "模型请求",
            call=self.calls,
            model=type(request.model).__name__,
            model_name=getattr(request.model, "model_name", None),
            system_prompt=request.system_prompt,
            model_settings=_dumps(request.model_settings),
            tool_choice=_dumps(request.tool_choice),
            tools=_dumps([_tool_payload(tool) for tool in request.tools]),
            messages=_dumps([message_to_dict(message) for message in request.messages]),
        )
        return self.calls

    # 打印模型返回的内容
    @staticmethod
    def _log_response(response: ModelResponse, call: int) -> None:
        logger.info(
            "模型响应",
            call=call,
            structured_response=_dumps(response.structured_response),
            messages=_dumps([message_to_dict(message) for message in response.result]),
        )

    # 包装同步模型调用
    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        call = self._log_request(request)
        response = handler(request)
        self._log_response(response, call)
        return response

    # 包装异步模型调用
    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        call = self._log_request(request)
        response = await handler(request)
        self._log_response(response, call)
        return response
