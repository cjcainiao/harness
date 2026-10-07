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
    def _append_text(
        self,
        kind: str,
        content: str,
        subagent: str | None = None,
        delegation_id: str | None = None,
    ) -> None:
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

        # 只有同一次委派的正文才并进同一段，主代理与子代理不互串
        last = self._segments[-1] if self._segments else None
        if (
            self._message_open
            and last is not None
            and last["kind"] == "message"
            and last.get("delegation_id") == delegation_id
        ):
            last["content"] += content
            return
        segment: dict[str, Any] = {"kind": "message", "content": content}
        if delegation_id is not None:
            segment["subagent"] = subagent
            segment["delegation_id"] = delegation_id
        self._segments.append(segment)
        self._message_open = True

    # 按调用标识或并行序号定位工具段，缺失时新建
    def _locate_tool(
        self, event: dict[str, Any], scope: str | None = None
    ) -> dict[str, Any] | None:
        call_id = event.get("tool_call_id")
        index = event.get("index")
        if not isinstance(call_id, str) and not isinstance(index, int):
            return None

        # 子代理的工具调用按委派分桶，不同委派里的同名调用不串段
        key = f"{scope}|{call_id}" if scope is not None and isinstance(call_id, str) else call_id

        position = None
        if isinstance(key, str):
            position = self._tool_by_call_id.get(key)
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

        if isinstance(key, str):
            segment["tool_call_id"] = call_id
            self._tool_by_call_id[key] = position
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
    def _handle_tool_start(
        self, event: dict[str, Any], scope: str | None = None
    ) -> dict[str, Any] | None:
        segment = self._locate_tool(event, scope)
        if segment is None:
            return None
        segment["status"] = STATUS_RUNNING
        if event.get("arguments") is not None:
            segment["arguments"] = event["arguments"]
        return segment

    # 处理工具结束，成功与失败分别写入状态和结果
    def _handle_tool_finish(
        self, event: dict[str, Any], status: str, scope: str | None = None
    ) -> dict[str, Any] | None:
        segment = self._locate_tool(event, scope)
        if segment is None:
            return None
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
        return segment

    # 把子代理名字标到宿主 task 段上，宿主段绝不带 delegation_id
    def _mark_host(self, delegation_id: str, subagent: str) -> None:
        position = self._tool_by_call_id.get(delegation_id)
        if position is None:
            return
        self._segments[position]["subagent"] = subagent

    # 处理子代理事件，落成与主代理同款的扁平段，只多挂两个标记
    def _handle_subagent(self, event: dict[str, Any]) -> None:
        sub_type = event.get("sub_type")
        delegation_id = event.get("delegation_id")
        subagent = event.get("subagent")
        if (
            not isinstance(sub_type, str)
            or not isinstance(delegation_id, str)
            or not isinstance(subagent, str)
        ):
            return

        if sub_type == "message_chunk":
            content = event.get("content")
            if isinstance(content, str) and content:
                self._append_text("message", content, subagent, delegation_id)
            return

        # 其余几档都结束当前正文段
        self._close_message()

        if sub_type == "start":
            self._mark_host(delegation_id, subagent)
            return

        if sub_type == "tool_start":
            segment = self._handle_tool_start(event, delegation_id)
        elif sub_type in {"tool_result", "tool_error"}:
            status = STATUS_SUCCESS if sub_type == "tool_result" else STATUS_ERROR
            segment = self._handle_tool_finish(event, status, delegation_id)
        else:
            # 收尾两条不再另起段
            return

        if segment is not None:
            segment["subagent"] = subagent
            segment["delegation_id"] = delegation_id

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
        # 明细计数：单次响应里的字段 → 本轮累计用的键
        detail_fields = (
            ("input_token_details", "cache_read", "cache_read_tokens"),
            ("output_token_details", "reasoning", "reasoning_tokens"),
        )
        counted: dict[str, int | None] = {}
        for source_key, field_key, total_key in detail_fields:
            details = raw.get(source_key)
            counted[total_key] = _read_count(details.get(field_key)) if isinstance(details, dict) else None
        if (
            input_tokens is None
            and output_tokens is None
            and total_tokens is None
            and all(value is None for value in counted.values())
        ):
            return

        previous = self._usage or {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        combined = total_tokens
        if combined is None:
            combined = (input_tokens or 0) + (output_tokens or 0)

        usage: dict[str, Any] = {
            "input_tokens": previous["input_tokens"] + (input_tokens or 0),
            "output_tokens": previous["output_tokens"] + (output_tokens or 0),
            "total_tokens": previous["total_tokens"] + combined,
        }
        for source_key, field_key, total_key in detail_fields:
            total = previous.get(total_key)
            if counted[total_key] is None and total is None:
                continue
            usage[total_key] = (total or 0) + (counted[total_key] or 0)
        self._usage = usage

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

        # 子代理事件走独立分支，其余分支都不认它
        if event_type == "subagent":
            self._handle_subagent(event)
            return

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
        elif event_type == "error":
            content = event.get("message")
            if isinstance(content, str) and content:
                self._segments.append({"kind": "error", "content": content})
