# 主代理

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver

from harness.agents.middlewares.builder import build_agent_middleware
from harness.agents.prompts.lead_agent import render_lead_agent_prompt
from harness.agents.thread_state import ThreadState
from harness.config.app_config import AppConfig, get_app_config
from harness.models.factory import ReasoningEffort, create_chat_model
from harness.subagents.registry import load_subagent_configs, subagents_section
from harness.skills.loader import load_skills, skills_section
from harness.tools.loader import load_default_tools
from harness.tools.system.tool_search import build_registry, deferred_tools_section


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
    checkpointer: BaseCheckpointSaver | None = None,
):
    config = app_config or get_app_config()

    # 根据本次请求动态创建模型
    model = create_chat_model(
        model_name=model_name,
        thinking_enabled=thinking_enabled,
        reasoning_effort=reasoning_effort,
        app_config=config,
    )

    # 工具绑定
    bound_tools = {tool.name: tool for tool in load_default_tools()}

    # 懒加载工具注册
    search_enabled = "tool_search" in bound_tools
    if search_enabled:
        bound_tools.update((tool.name, tool) for tool in build_registry())

    bound_tools.update((tool.name, tool) for tool in tools or ())

    # 系统提示词渲染
    prompt = render_lead_agent_prompt(
        role=system_prompt,
        deferred_tools=deferred_tools_section() if search_enabled else "",
        skills=skills_section(load_skills()),
        subagents=subagents_section(load_subagent_configs()),
    )

    # 主代理组装
    return create_agent(
        model=model,
        tools=list(bound_tools.values()),
        middleware=build_agent_middleware(middleware),
        state_schema=ThreadState,
        system_prompt=prompt,
        checkpointer=checkpointer,
        debug=config.system.debug,
        name="lead-agent",
    )
