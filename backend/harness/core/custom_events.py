# 自定义事件

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.callbacks import adispatch_custom_event, dispatch_custom_event
from langgraph.errors import GraphBubbleUp

from harness.core.logger import get_logger


logger = get_logger(__name__)

StreamWriter = Callable[[Any], None]


# 获取自定义事件名称
def _get_event_name(payload: dict[str, Any]) -> str | None:
    event_type = payload.get("type")
    if isinstance(event_type, str) and event_type:
        return event_type

    logger.debug("自定义事件缺少有效的 type 字段，跳过回调分发")
    return None


# 发送同步自定义事件
def emit_custom_event(payload: dict[str, Any], *, writer: StreamWriter) -> None:
    # custom 流是主要发送通道
    writer(payload)

    event_name = _get_event_name(payload)
    if event_name is None:
        return

    try:
        dispatch_custom_event(event_name, payload)
    except GraphBubbleUp:
        # 保留 LangGraph 的中断和控制流语义
        raise
    except Exception:
        # 回调通道失败不能影响 custom 流和主代理执行
        logger.debug(
            "自定义事件回调分发失败",
            event_name=event_name,
            exc_info=True,
        )


# 发送异步自定义事件
async def aemit_custom_event(payload: dict[str, Any], *, writer: StreamWriter) -> None:
    # custom 流是主要发送通道
    writer(payload)

    event_name = _get_event_name(payload)
    if event_name is None:
        return

    try:
        await adispatch_custom_event(event_name, payload)
    except GraphBubbleUp:
        # 保留 LangGraph 的中断和控制流语义
        raise
    except Exception:
        # 回调通道失败不能影响 custom 流和主代理执行
        logger.debug(
            "异步自定义事件回调分发失败",
            event_name=event_name,
            exc_info=True,
        )
