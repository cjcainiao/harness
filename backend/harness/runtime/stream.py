# Agent 流式运行

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.errors import GraphBubbleUp

from harness.agents.lead_agent import Tool, create_lead_agent
from harness.config.app_config import get_app_config
from harness.core.logger import get_logger
from harness.models.factory import ReasoningEffort
from harness.runtime.checkpointer import get_checkpointer
from harness.storage import history
from harness.storage.recorder import TurnRecorder


logger = get_logger(__name__)


# 触发进度落库的事件类型
MILESTONE_TYPES = frozenset({"usage", "tool_result", "tool_error"})


# 转换JSON默认值
def _json_default(value: Any) -> Any:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    return str(value)


# 转换SSE事件
def _encode_sse(payload: dict[str, Any]) -> str:
    data = json.dumps(
        payload,
        ensure_ascii=False,
        default=_json_default,
        separators=(",", ":"),
    )
    return f"data: {data}\n\n"


# 添加事件来源
def _with_source(
    payload: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    namespace: Sequence[str] | None = None,
) -> dict[str, Any]:
    event = dict(payload)

    if metadata:
        source = metadata.get("langgraph_node")
        if source:
            event["source"] = source

    if namespace:
        event["namespace"] = list(namespace)

    return event


# 解析模型流式消息
def _parse_message_events(
    message: Any,
    metadata: dict[str, Any] | None,
    namespace: Sequence[str] | None,
) -> list[dict[str, Any]]:
    # 工具结果由工具调用中间件发送
    if isinstance(message, ToolMessage):
        return []

    events: list[dict[str, Any]] = []

    try:
        content_blocks = message.content_blocks
    except (AttributeError, TypeError, ValueError):
        content_blocks = []

    for block in content_blocks:
        if not isinstance(block, dict):
            continue

        block_type = block.get("type")
        if block_type in {"text", "text-plain"}:
            content = block.get("text")
            if isinstance(content, str) and content:
                events.append(
                    _with_source(
                        {"type": "message_chunk", "content": content},
                        metadata,
                        namespace,
                    )
                )
        elif block_type == "reasoning":
            content = block.get("reasoning")
            if isinstance(content, str) and content:
                events.append(
                    _with_source(
                        {"type": "reasoning_chunk", "content": content},
                        metadata,
                        namespace,
                    )
                )
        elif block_type in {"tool_call_chunk", "server_tool_call_chunk"}:
            events.append(
                _with_source(
                    {
                        "type": "tool_call_chunk",
                        "tool": block.get("name"),
                        "tool_call_id": block.get("id"),
                        "index": block.get("index"),
                        "arguments": block.get("args"),
                    },
                    metadata,
                    namespace,
                )
            )

    # 兼容未提供标准内容块的模型
    if not events:
        content = getattr(message, "content", None)
        if isinstance(content, str) and content:
            events.append(
                _with_source(
                    {"type": "message_chunk", "content": content},
                    metadata,
                    namespace,
                )
            )

    usage = getattr(message, "usage_metadata", None)
    if usage:
        events.append(
            _with_source(
                {"type": "usage", "usage": usage},
                metadata,
                namespace,
            )
        )

    return events


# 开启历史轮次，失败时返回 None 表示本轮不入库
def _start_turn(thread_id: str, question: str) -> str | None:
    try:
        return history.start_turn(thread_id, question)
    except sqlite3.Error as error:
        logger.warning("历史轮次创建失败", thread_id=thread_id, error=str(error))
        return None


# 执行主代理并返回SSE流
async def stream_agent(
    message: str,
    model_name: str | None = None,
    thinking_enabled: bool = False,
    reasoning_effort: ReasoningEffort | None = None,
    *,
    thread_id: str | None = None,
    tools: Sequence[Tool] | None = None,
    middleware: Sequence[AgentMiddleware] | None = None,
    system_prompt: str | None = None,
) -> AsyncIterator[str]:
    # 会话标识缺失时由服务端生成，历史才有归属
    thread_id = thread_id or uuid.uuid4().hex
    run_config = {"configurable": {"thread_id": thread_id}}

    recorder = TurnRecorder()
    turn_id = _start_turn(thread_id, message)

    # 覆盖轮次进度或收尾状态，写库失败不打断回复
    def save(status: str) -> None:
        if turn_id is None:
            return
        try:
            history.update_turn(turn_id, status, recorder.segments(), recorder.usage())
        except sqlite3.Error as error:
            logger.warning("历史写入失败", turn_id=turn_id, error=str(error))

    # 事件先攒段，到关键节点落库，断开时也能保住已有内容
    def track(event: dict[str, Any]) -> None:
        recorder.feed(event)
        if event.get("type") in MILESTONE_TYPES:
            save(history.TURN_STREAMING)

    final_status = history.TURN_COMPLETED

    try:
        agent = create_lead_agent(
            model_name=model_name,
            thinking_enabled=thinking_enabled,
            reasoning_effort=reasoning_effort,
            tools=tools,
            middleware=middleware,
            system_prompt=system_prompt,
            checkpointer=get_checkpointer(),
        )

        # 输入只给当轮消息，历史由 thread_id 从检查点取回
        async for chunk in agent.astream(
            {"messages": [{"role": "user", "content": message}]},
            config=run_config,
            durability=get_app_config().memory.durability,
            stream_mode=["messages", "custom"],
            subgraphs=True,
            version="v2",
        ):
            stream_type = chunk.get("type")
            data = chunk.get("data")
            namespace = chunk.get("ns")

            if stream_type == "messages":
                message_chunk, metadata = data
                for event in _parse_message_events(
                    message_chunk,
                    metadata,
                    namespace,
                ):
                    track(event)
                    yield _encode_sse(event)

            elif stream_type == "custom":
                if isinstance(data, dict):
                    event = dict(data)
                    event.setdefault("type", "custom")
                else:
                    event = {"type": "custom", "data": data}

                if namespace:
                    event.setdefault("namespace", list(namespace))

                track(event)
                yield _encode_sse(event)

        yield _encode_sse({"type": "done", "thread_id": thread_id})

    except asyncio.CancelledError:
        logger.info("客户端已断开流式连接", thread_id=thread_id)
        raise
    except GraphBubbleUp:
        # 保留 LangGraph 的中断和恢复语义
        raise
    except Exception as error:
        final_status = history.TURN_FAILED
        logger.error(
            "主代理流式执行失败",
            thread_id=thread_id,
            error=str(error),
            exc_info=True,
        )
        yield _encode_sse(
            {
                "type": "error",
                "code": 500,
                "message": "服务器内部错误",
            }
        )
    finally:
        # 补一次结束事件，定格没有闭合的推理段
        recorder.feed({"type": "done"})
        save(final_status)
