# Agent 流式运行

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langgraph.errors import GraphBubbleUp

from harness.agents.lead_agent import Tool, create_lead_agent
from harness.agents.thread_state import UploadedFileInfo
from harness.config.app_config import get_app_config
from harness.core.logger import get_logger
from harness.models.factory import ReasoningEffort
from harness.agents.memory.checkpointer import get_checkpointer
from harness.runtime.events import parse_message_events
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


# 开启历史轮次，失败时返回 None 表示本轮不入库
def _start_turn(thread_id: str, question: str, uploaded_files: Sequence[UploadedFileInfo]) -> str | None:
    try:
        return history.start_turn(thread_id, question, uploaded_files)
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
    uploaded_files: Sequence[UploadedFileInfo] = (),
    tools: Sequence[Tool] | None = None,
    middleware: Sequence[AgentMiddleware] | None = None,
    system_prompt: str | None = None,
) -> AsyncIterator[str]:
    # 会话标识缺失时由服务端生成，历史才有归属
    thread_id = thread_id or uuid.uuid4().hex
    run_config = {"configurable": {"thread_id": thread_id}}

    recorder = TurnRecorder()
    turn_id = _start_turn(thread_id, message, uploaded_files)

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

    # 只有代理完整跑完才算完成；取消或控制流中断保留为中断
    final_status = history.TURN_INTERRUPTED

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

        # 本轮附件状态
        async for chunk in agent.astream(
            {
                "messages": [{"role": "user", "content": message}],
                "uploaded_files": list(uploaded_files),
            },
            config=run_config,
            durability=get_app_config().memory.durability,
            stream_mode=["messages", "custom"],
            subgraphs=False,
            version="v2",
        ):
            stream_type = chunk.get("type")
            data = chunk.get("data")
            namespace = chunk.get("ns")

            if stream_type == "messages":
                message_chunk, metadata = data
                for payload in parse_message_events(message_chunk):
                    event = _with_source(payload, metadata, namespace)
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

        final_status = history.TURN_COMPLETED
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
        event = {
            "type": "error",
            "code": 500,
            "message": "服务器内部错误",
        }
        # 失败提示攒进渲染段，收尾时才有内容可写
        track(event)
        yield _encode_sse(event)
    finally:
        # 补一次结束事件，定格没有闭合的推理段
        recorder.feed({"type": "done"})
        save(final_status)
