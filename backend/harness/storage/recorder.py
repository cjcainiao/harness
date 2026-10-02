# 轮次事件聚合器

from __future__ import annotations

import time
from typing import Any


# 工具段的状态取值
STATUS_PREPARING = "preparing"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"

# 会结束当前正文段的事件类型
MESSAGE_CLOSING_TYPES = frozenset(
    {
        "reasoning_chunk",
        "tool_call_chunk",
        "tool_start",
        "tool_result",
        "tool_error",
        "done",
        "error",
    }
)


# 读取合法 Token 计数，非法值按缺失处理
def _read_count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None


# 把一次回复的事件流攒成渲染段
class TurnRecorder:
    def __init__(self) -> None:
        self._segments: list[dict[str, Any]] = []
        self._usage: dict[str, Any] | None = None
        self._message_open = False
        self._reasoning_start: float | None = None
        self._tool_by_call_id: dict[str, int] = {}
        self._tool_by_index: dict[int, int] = {}

    # 攒段结果，顺序即显示顺序
    def segments(self) -> list[dict[str, Any]]:
        return [dict(segment) for segment in self._segments]

    # 本轮累计 Token 用量，没有用量事件时为空
    def usage(self) -> dict[str, Any] | None:
        return dict(self._usage) if self._usage else None

    # 结束当前正文段，下一段文字另起一项
    def _close_message(self) -> None:
        self._message_open = False

    # 结束当前推理段并定格耗时
    def _close_reasoning(self) -> None:
        started_at = self._reasoning_start
        self._reasoning_start = None
        if started_at is None:
            return
        last = self._segments[-1] if self._segments else None
        if last is not None and last.get("kind") == "reasoning":
            last["duration_ms"] = round((time.monotonic() - started_at) * 1000)

    # 追加文字到当前段，段已结束时另起一段
    def _append_text(self, kind: str, content: str) -> None:
        if kind == "reasoning":
            # 推理段只在相邻时合并
            last = self._segments[-1] if self._segments else None
            if last is not None and last.get("kind") == "reasoning":
                last["content"] += content
                self._reasoning_start = self._reasoning_start or time.monotonic()
                return
            self._segments.append({"kind": kind, "content": content, "duration_ms": 0})
            self._reasoning_start = time.monotonic()
            return

        if self._message_open and self._segments and self._segments[-1]["kind"] == "message":
            self._segments[-1]["content"] += content
            return
        self._segments.append({"kind": "message", "content": content})
        self._message_open = True

    # 按调用标识或并行序号定位工具段，缺失时新建
    def _locate_tool(self, event: dict[str, Any]) -> dict[str, Any] | None:
        call_id = event.get("tool_call_id")
        index = event.get("index")
        if not isinstance(call_id, str) and not isinstance(index, int):
            return None

        position = None
        if isinstance(call_id, str):
            position = self._tool_by_call_id.get(call_id)
        if position is None and isinstance(index, int):
            indexed = self._tool_by_index.get(index)
            if indexed is not None:
                candidate = self._segments[indexed]
                owned = candidate.get("tool_call_id")
                # 已归属其他调用的序号不再复用
                if owned is None or not isinstance(call_id, str) or owned == call_id:
                    position = indexed

        if position is None:
            position = len(self._segments)
            self._segments.append(
                {
                    "kind": "tool",
                    "tool": "",
                    "tool_call_id": call_id if isinstance(call_id, str) else None,
                    "status": STATUS_PREPARING,
                    "arguments": None,
                    "output": None,
                    "duration_ms": None,
                }
            )
            segment = self._segments[position]
        else:
            segment = self._segments[position]

        if isinstance(call_id, str):
            segment["tool_call_id"] = call_id
            self._tool_by_call_id[call_id] = position
        if isinstance(index, int):
            self._tool_by_index[index] = position
        if isinstance(event.get("tool"), str):
            segment["tool"] = event["tool"]
        return segment

    # 参数分片按文本累加，完整参数由 tool_start 覆盖
    def _append_arguments(self, segment: dict[str, Any], fragment: Any) -> None:
        if not isinstance(fragment, str):
            return
        current = segment["arguments"]
        segment["arguments"] = (current if isinstance(current, str) else "") + fragment

    # 处理工具开始，写入完整参数
    def _handle_tool_start(self, event: dict[str, Any]) -> None:
        segment = self._locate_tool(event)
        if segment is None:
            return
        segment["status"] = STATUS_RUNNING
        if event.get("arguments") is not None:
            segment["arguments"] = event["arguments"]

    # 处理工具结束，成功与失败分别写入状态和结果
    def _handle_tool_finish(self, event: dict[str, Any], status: str) -> None:
        segment = self._locate_tool(event)
        if segment is None:
            return
        segment["status"] = status
        if status == STATUS_ERROR:
            segment["output"] = event.get("content")
            if segment["output"] is None:
                segment["output"] = event.get("message")
        else:
            if event.get("content") is not None:
                segment["output"] = event["content"]
        duration = event.get("duration_ms")
        if isinstance(duration, (int, float)):
            segment["duration_ms"] = round(duration)

    # 累计单次模型响应的 Token 用量
    def _handle_usage(self, event: dict[str, Any]) -> None:
        # 一轮模型响应结束，序号定位的工具索引失效
        self._tool_by_index.clear()

        raw = event.get("usage")
        if not isinstance(raw, dict):
            return

        input_tokens = _read_count(raw.get("input_tokens"))
        output_tokens = _read_count(raw.get("output_tokens"))
        total_tokens = _read_count(raw.get("total_tokens"))
        details = raw.get("input_token_details")
        cache_read = None
        if isinstance(details, dict):
            cache_read = _read_count(details.get("cache_read"))
        if (
            input_tokens is None
            and output_tokens is None
            and total_tokens is None
            and cache_read is None
        ):
            return

        previous = self._usage or {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        cache_total = previous.get("cache_read_tokens")
        if cache_read is None and cache_total is None:
            cache_next = None
        else:
            cache_next = (cache_total or 0) + (cache_read or 0)

        combined = total_tokens
        if combined is None:
            combined = (input_tokens or 0) + (output_tokens or 0)

        self._usage = {
            "input_tokens": previous["input_tokens"] + (input_tokens or 0),
            "output_tokens": previous["output_tokens"] + (output_tokens or 0),
            "total_tokens": previous["total_tokens"] + combined,
        }
        if cache_next is not None:
            self._usage["cache_read_tokens"] = cache_next

    # 吃一个事件，按类型写入对应的段
    def feed(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if not isinstance(event_type, str):
            return

        # 除推理片段本身，其他事件都表示上一段推理已结束
        if event_type != "reasoning_chunk":
            self._close_reasoning()

        if event_type == "message_chunk":
            content = event.get("content")
            if isinstance(content, str) and content:
                self._append_text("message", content)
            return

        if event_type in MESSAGE_CLOSING_TYPES:
            self._close_message()

        if event_type == "reasoning_chunk":
            content = event.get("content")
            if isinstance(content, str) and content:
                self._append_text("reasoning", content)
        elif event_type == "tool_call_chunk":
            segment = self._locate_tool(event)
            if segment is not None:
                self._append_arguments(segment, event.get("arguments"))
        elif event_type == "tool_start":
            self._handle_tool_start(event)
        elif event_type == "tool_result":
            self._handle_tool_finish(event, STATUS_SUCCESS)
        elif event_type == "tool_error":
            self._handle_tool_finish(event, STATUS_ERROR)
        elif event_type == "usage":
            self._handle_usage(event)
