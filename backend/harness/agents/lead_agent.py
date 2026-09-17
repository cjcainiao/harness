# 主代理

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import BaseTool

from harness.config.app_config import AppConfig, get_app_config
from harness.models.factory import ReasoningEffort, create_chat_model


Tool = BaseTool | Callable[..., Any] | dict[str, Any]

DEFAULT_SYSTEM_PROMPT = """你是 Harness 的主代理，负责理解用户目标并选择合适的工具完成任务。
需要调用工具时先调用工具，完成后根据真实结果回答；无论是否调用工具，最后都要向用户提供清晰的结果。"""


# 创建主代理
def create_lead_agent(
    model_name: str | None = None,
    thinking_enabled: bool = False,
    reasoning_effort: ReasoningEffort | None = None,
    *,
    app_config: AppConfig | None = None,
    tools: Sequence[Tool] | None = None,
    middleware: Sequence[AgentMiddleware] | None = None,
    system_prompt: str | None = None,
):
    config = app_config or get_app_config()

    # 根据本次请求动态创建模型
    model = create_chat_model(
        name=model_name,
        thinking_enabled=thinking_enabled,
        reasoning_effort=reasoning_effort,
        app_config=config,
    )

    # 统一组装模型、工具、中间件和系统提示词
    return create_agent(
        model=model,
        tools=list(tools or ()),
        middleware=list(middleware or ()),
        system_prompt=system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT,
        debug=config.system.debug,
        name="lead-agent",
    )
