# 子代理委派工具

from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, ConfigDict, Field

from harness.models.factory import ReasoningEffort
from harness.runtime.events import parse_message_events
from harness.subagents.factory import create_subagent, subagent_recursion_limit
from harness.subagents.registry import get_subagent_config


# 子代理事件的对外类型标识
SUBAGENT_EVENT = "subagent"

# 原样转发的工具事件类型
TOOL_SUB_TYPES = frozenset({"tool_start", "tool_result", "tool_error"})

# 委派内工具参数的最长字符数
ARGUMENTS_LIMIT = 120


# 委派入参，runtime 由框架注入，不暴露给模型
class TaskArgs(BaseModel):
    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    agent: str = Field(description="子代理名称，必须来自可用子代理清单")
    prompt: str = Field(description="交给子代理的任务描述，一次写清目标、范围和交付物")
    runtime: ToolRuntime


# 取本轮主代理的模型口径，metadata 缺失时按默认模型处理
def _turn_model(runtime: ToolRuntime) -> tuple[str | None, bool, ReasoningEffort | None]:
    metadata = (runtime.config or {}).get("metadata") or {}
    model_name = metadata.get("model_name")
    thinking_enabled = bool(metadata.get("thinking_enabled"))
    reasoning_effort = metadata.get("reasoning_effort")
    return (
        model_name if isinstance(model_name, str) else None,
        thinking_enabled,
        reasoning_effort if isinstance(reasoning_effort, str) else None,
    )


# 发送一条子代理事件，字段与主代理同款
def _emit(
    runtime: ToolRuntime, subagent: str, sub_type: str, fields: dict[str, Any] | None = None
) -> None:
    runtime.stream_writer(
        {
            "type": SUBAGENT_EVENT,
            "sub_type": sub_type,
            "subagent": subagent,
            "delegation_id": runtime.tool_call_id,
            **(fields or {}),
        }
    )


# 参数压成字符串并截断，结果正文不截
def _cut_arguments(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text[:ARGUMENTS_LIMIT]


# 转发子代理中间件发出的工具事件
def _forward_tool_event(
    runtime: ToolRuntime, subagent: str, payload: dict[str, Any]
) -> None:
    sub_type = payload.get("type")
    if not isinstance(sub_type, str) or sub_type not in TOOL_SUB_TYPES:
        return

    fields = {key: value for key, value in payload.items() if key != "type"}
    if "arguments" in fields:
        fields["arguments"] = _cut_arguments(fields["arguments"])

    _emit(runtime, subagent, sub_type, fields)


# 取消息正文，内容块形态只取文字部分
def _text_of(message: Any) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = (
            str(block.get("text", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
        return "".join(parts)
    return ""


# 倒着找子代理最后一条有文字的回复作为交付物
def _conclusion(messages: list[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = _text_of(message).strip()
            if text:
                return text
    return ""


# 边读边转发子代理事件，返回它跑完的消息轨迹
async def _collect(
    subagent: Any,
    prompt: str,
    subagent_name: str,
    runtime: ToolRuntime,
    recursion_limit: int,
) -> list[Any]:
    messages: list[Any] = []

    async for chunk in subagent.astream(
        {"messages": [HumanMessage(content=prompt)]},
        config={"recursion_limit": recursion_limit},
        stream_mode=["messages", "custom", "updates"],
    ):
        mode, data = chunk

        if mode == "messages":
            message_chunk, _metadata = data
            for payload in parse_message_events(message_chunk):
                payload_type = payload.get("type")
                if payload_type == "message_chunk":
                    _emit(
                        runtime,
                        subagent_name,
                        "message_chunk",
                        {"content": payload["content"]},
                    )
                elif payload_type == "usage":
                    # 用量原样转发，不带委派标记，父子按同一口径累加进本轮
                    runtime.stream_writer(payload)

        elif mode == "custom" and isinstance(data, dict):
            _forward_tool_event(runtime, subagent_name, data)

        elif mode == "updates" and isinstance(data, dict):
            for update in data.values():
                if not isinstance(update, dict):
                    continue
                new_messages = update.get("messages")
                if isinstance(new_messages, list):
                    messages.extend(new_messages)

    return messages


# 一次委派的错误文案，异常本身没有文字时退到类型名
def _error_text(error: BaseException) -> str:
    return str(error) or error.__class__.__name__


# 执行一次委派，过程实时播报，只返回最终交付物
async def _delegate(agent: str, prompt: str, runtime: ToolRuntime) -> dict[str, str]:
    config = get_subagent_config(agent)
    model_name, thinking_enabled, reasoning_effort = _turn_model(runtime)

    subagent = create_subagent(
        agent,
        model_name=model_name,
        thinking_enabled=thinking_enabled,
        reasoning_effort=reasoning_effort,
    )

    _emit(runtime, config.name, "start")

    try:
        messages = await asyncio.wait_for(
            _collect(subagent, prompt, config.name, runtime, subagent_recursion_limit(config)),
            timeout=config.timeout_seconds,
        )
    except TimeoutError as error:
        # 超时原本的 str() 是空的，直接上抛会让模型看到空白错误
        message = f"子代理执行超时：{config.timeout_seconds} 秒"
        _emit(runtime, config.name, "error", {"message": message})
        raise TimeoutError(message) from error
    except Exception as error:
        _emit(runtime, config.name, "error", {"message": _error_text(error)})
        raise

    _emit(runtime, config.name, "finish")

    return {"agent": config.name, "result": _conclusion(messages)}


@tool("task", args_schema=TaskArgs)
async def task(agent: str, prompt: str, runtime: ToolRuntime) -> str:
    """把一整块任务委派给子代理去做，子代理会自己多轮调用工具直到完成。

    适合范围大、步骤多、需要翻不少文件才能得出结论的事。委派内容要一次写清
    目标、范围和要交付的东西，子代理看不到本轮对话历史，也不会向用户提问。

    Args:
        agent: 子代理名称，必须是可用子代理清单里的名字。
        prompt: 任务描述，包含目标、范围和期望交付的结果形式。

    Returns:
        JSON 对象字符串，含两个字段：
        - agent: 实际执行的子代理名称
        - result: 子代理的最终交付物原文，可能为空字符串
    """
    return json.dumps(await _delegate(agent, prompt, runtime), ensure_ascii=False)
