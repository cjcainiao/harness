# 模型消息事件翻译

from __future__ import annotations

from typing import Any

from langchain_core.messages import ToolMessage


# 把一条流式消息翻成事件列表，来源标记由调用方补
def parse_message_events(message: Any) -> list[dict[str, Any]]:
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
                events.append({"type": "message_chunk", "content": content})
        elif block_type == "reasoning":
            content = block.get("reasoning")
            if isinstance(content, str) and content:
                events.append({"type": "reasoning_chunk", "content": content})
        elif block_type in {"tool_call_chunk", "server_tool_call_chunk"}:
            events.append(
                {
                    "type": "tool_call_chunk",
                    "tool": block.get("name"),
                    "tool_call_id": block.get("id"),
                    "index": block.get("index"),
                    "arguments": block.get("args"),
                }
            )

    # 兼容未提供标准内容块的模型
    if not events:
        content = getattr(message, "content", None)
        if isinstance(content, str) and content:
            events.append({"type": "message_chunk", "content": content})

    usage = getattr(message, "usage_metadata", None)
    if usage:
        events.append({"type": "usage", "usage": usage})

    return events
