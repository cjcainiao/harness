# 主代理

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import BaseTool

from harness.agents.middlewares.builder import build_agent_middleware
from harness.agents.prompts.lead_agent import render_lead_agent_prompt
from harness.config.app_config import AppConfig, get_app_config
from harness.models.factory import ReasoningEffort, create_chat_model
from harness.tools.loader import load_default_tools
from harness.tools.tool_search import build_registry, deferred_tools_section


Tool = BaseTool | Callable[..., Any] | dict[str, Any]


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

    # 默认工具与传入工具共存，同名时传入的优先
    bound_tools = {tool.name: tool for tool in load_default_tools()}

    # 懒加载开启时注册非默认组工具
    if config.tool_search.get("enabled"):
        bound_tools.update((tool.name, tool) for tool in build_registry())

    bound_tools.update((tool.name, tool) for tool in tools or ())

    # 渲染系统提示词，自定义内容只替换身份段，规则与懒加载名单始终拼接
    prompt = render_lead_agent_prompt(
        role=system_prompt,
        deferred_tools=deferred_tools_section(),
    )

    # 统一组装模型、工具、中间件和系统提示词
    return create_agent(
        model=model,
        tools=list(bound_tools.values()),
        middleware=build_agent_middleware(middleware),
        system_prompt=prompt,
        debug=config.system.debug,
        name="lead-agent",
    )
