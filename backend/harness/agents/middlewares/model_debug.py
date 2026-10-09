# 模型调用调试中间件

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, override

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import message_to_dict
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_function
from langgraph.config import get_config

from harness.core.logger import get_logger
from harness.agents.memory.checkpointer import get_checkpointer


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

    # 打印检查点回载到的内容，序号与紧随其后的模型请求对齐
    async def _log_checkpoint(self) -> None:
        call = self.calls + 1
        checkpointer = get_checkpointer()
        if checkpointer is None:
            logger.info("检查点回载", call=call, checkpointer="未初始化")
            return

        config = get_config()
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id is None:
            logger.info("检查点回载", call=call, checkpointer="无 thread_id")
            return

        try:
            # 节点内 ns 是 model:task_id，主代理历史只存在 ns 为空串的那份
            loaded = await checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})
        except Exception as error:
            # 调试读库失败不打断模型调用
            logger.warning("检查点回载读取失败", call=call, thread_id=thread_id, error=str(error))
            return

        if loaded is None:
            logger.info("检查点回载", call=call, thread_id=thread_id, checkpoint="该会话无历史")
            return

        checkpoint = loaded.checkpoint
        messages = checkpoint["channel_values"].get("messages", [])
        parent_config = loaded.parent_config or {}
        logger.info(
            "检查点回载",
            call=call,
            thread_id=thread_id,
            checkpoint_id=checkpoint["id"],
            parent_checkpoint_id=parent_config.get("configurable", {}).get("checkpoint_id"),
            step=loaded.metadata.get("step"),
            source=loaded.metadata.get("source"),
            channels=_dumps(sorted(checkpoint["channel_values"])),
            message_count=len(messages),
            messages=_dumps([message_to_dict(message) for message in messages]),
        )

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
        await self._log_checkpoint()
        call = self._log_request(request)
        response = await handler(request)
        self._log_response(response, call)
        return response
