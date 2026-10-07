# 子代理工厂

from __future__ import annotations

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_core.tools import BaseTool

from harness.agents.middlewares.tool_call import ToolCallMiddleware
from harness.agents.thread_state import ThreadState
from harness.config.app_config import AppConfig, get_app_config
from harness.models.factory import ReasoningEffort, create_chat_model
from harness.subagents.registry import SubagentConfig, get_subagent_config
from harness.tools.loader import enabled_items, import_tool


# 跟随本轮主代理的模型关键字，与配置里 model: inherit 同值
INHERIT_MODEL = "inherit"

# 子代理不得再委派子代理，委派工具在取工具池时写死剔除
NO_RECURSION_TOOL = "task"

# 一轮模型调用占用的超步数与预留余量
STEPS_PER_TURN = 4
STEPS_HEADROOM = 4


# 一次委派的图超步上限，步数闸门比它先起效
def subagent_recursion_limit(config: SubagentConfig) -> int:
    return config.max_turns * STEPS_PER_TURN + STEPS_HEADROOM


# 按配置取生效模型名，inherit 跟随本轮主代理，不填走默认模型
def resolve_model_name(config: SubagentConfig, model_name: str | None) -> str | None:
    if config.model is None:
        return None
    if config.model == INHERIT_MODEL:
        return model_name
    return config.model


# 全部已启用工具，按工具名建索引
def _tool_pool() -> dict[str, BaseTool]:
    pool: dict[str, BaseTool] = {}
    for is_default in (True, False):
        for item in enabled_items(is_default):
            tool = import_tool(item.get("use"))
            pool[tool.name] = tool

    # 委派工具不进气池，子代理拿不到也就调不出递归
    pool.pop(NO_RECURSION_TOOL, None)
    return pool


# 按子代理名单取工具对象
def _resolve_tools(config: SubagentConfig) -> list[BaseTool]:
    pool = _tool_pool()
    return [pool[name] for name in config.enabled_tools(pool)]


# 建出一个可直接执行的子代理
def create_subagent(
    name: str,
    *,
    model_name: str | None = None,
    thinking_enabled: bool = False,
    reasoning_effort: ReasoningEffort | None = None,
    app_config: AppConfig | None = None,
):
    config = get_subagent_config(name)
    app = app_config or get_app_config()

    model = create_chat_model(
        name=resolve_model_name(config, model_name),
        thinking_enabled=thinking_enabled,
        reasoning_effort=reasoning_effort,
        app_config=app,
    )

    return create_agent(
        model=model,
        tools=_resolve_tools(config),
        middleware=[
            ToolCallMiddleware(),
            ModelCallLimitMiddleware(run_limit=config.max_turns),
        ],
        state_schema=ThreadState,
        system_prompt=config.system_prompt,
        checkpointer=False,
        name=config.name,
    )
