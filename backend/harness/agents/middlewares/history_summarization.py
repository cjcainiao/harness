# 历史消息总结中间件

from __future__ import annotations

from typing import Any, override

from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain_core.messages import AnyMessage
from langgraph.runtime import Runtime


# 达到阈值时压缩历史消息
class HistorySummarizationMiddleware(AgentMiddleware):
    # 改写 state 而不是拦 handler
    @override
    async def abefore_model(
        self, state: AgentState[Any], runtime: Runtime[Any]
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    # 是否达到压缩阈值
    @staticmethod
    def _over_threshold(messages: list[AnyMessage]) -> bool:
        raise NotImplementedError

    # 找压缩边界，保证 tool_calls 与工具结果成对
    @staticmethod
    def _find_cutoff(messages: list[AnyMessage]) -> int:
        raise NotImplementedError

    # 调总结子代理生成摘要文本
    @staticmethod
    async def _summarize(messages: list[AnyMessage]) -> str | None:
        raise NotImplementedError

    # 组装重写列表，先移除全部消息
    @staticmethod
    def _build_updates(summary: str, kept: list[AnyMessage]) -> dict[str, Any]:
        raise NotImplementedError
