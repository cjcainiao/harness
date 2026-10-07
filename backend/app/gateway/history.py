# 会话历史接口

from typing import Any

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.result import Result
from harness.storage import history


router = APIRouter(prefix="/chat", tags=["会话历史"])


# 轮次渲染段
class TurnItemInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(description="段类型，取值 message / reasoning / tool / error")
    content: str | None = Field(default=None, description="正文、推理或失败提示文本")
    duration_ms: int | None = Field(default=None, description="本段耗时，单位毫秒")
    tool: str | None = Field(default=None, description="工具名称")
    tool_call_id: str | None = Field(default=None, description="工具调用标识")
    status: str | None = Field(
        default=None, description="工具状态，取值 preparing / running / success / error"
    )
    arguments: dict[str, Any] | str | None = Field(default=None, description="工具入参")
    output: Any = Field(default=None, description="工具返回内容")
    subagent: str | None = Field(default=None, description="执行这段的子代理名称")
    delegation_id: str | None = Field(default=None, description="所属委派标识")


# Token 用量
class UsageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int = Field(description="输入 Token 数")
    output_tokens: int = Field(description="输出 Token 数")
    total_tokens: int = Field(description="总 Token 数")
    cache_read_tokens: int | None = Field(default=None, description="缓存命中的输入 Token 数")
    reasoning_tokens: int | None = Field(default=None, description="推理消耗的输出 Token 数")


# 会话摘要
class ThreadInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str = Field(description="会话标识")
    title: str = Field(description="会话标题")
    created_at: str = Field(description="创建时间，ISO-8601 UTC")
    updated_at: str = Field(description="最后活动时间，ISO-8601 UTC")
    input_tokens: int = Field(description="会话累计输入 Token")
    output_tokens: int = Field(description="会话累计输出 Token")


# 一轮问答
class TurnInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: str = Field(description="轮次标识")
    thread_id: str = Field(description="所属会话")
    seq: int = Field(description="会话内序号")
    question: str = Field(description="提问原文")
    status: str = Field(description="轮次状态，取值 completed / failed")
    created_at: str = Field(description="提问时间，ISO-8601 UTC")
    items: list[TurnItemInfo] = Field(description="渲染段，顺序即显示顺序")
    usage: UsageInfo | None = Field(default=None, description="本轮累计用量")


# 未收尾的轮次按已完成返回
def _terminal_status(status: str) -> str:
    return history.TURN_COMPLETED if status == history.TURN_STREAMING else status


# 会话列表，游标指向上一页最后一条
@router.get("/threads", summary="获取会话列表")
async def get_threads(
    limit: int = Query(default=50, ge=1, le=200, description="返回条数上限"),
    before_created_at: str | None = Query(
        default=None, max_length=32, description="游标创建时间，ISO-8601 UTC"
    ),
    before_thread_id: str | None = Query(
        default=None, max_length=128, description="游标会话标识，同一秒内区分先后"
    ),
) -> Result[list[ThreadInfo]]:
    # 游标两项必须成对，只给一项会翻出重复数据
    if (before_created_at is None) != (before_thread_id is None):
        return Result.error(code=400, message="翻页游标需要同时给出创建时间和会话标识")

    cursor = (
        (before_created_at, before_thread_id)
        if before_created_at and before_thread_id
        else None
    )
    threads = [ThreadInfo(**thread) for thread in await history.list_threads(limit, cursor)]
    return Result.success(threads)


# 会话内的历史轮次，游标是已加载最早一轮的序号
@router.get("/threads/{thread_id}/turns", summary="获取会话历史轮次")
async def get_thread_turns(
    thread_id: str = Path(min_length=1, max_length=128, description="会话标识"),
    limit: int = Query(default=20, ge=1, le=100, description="返回条数上限"),
    before_seq: int | None = Query(default=None, ge=1, description="游标序号，只取比它更早的轮次"),
) -> Result[list[TurnInfo]]:
    if await history.get_thread(thread_id) is None:
        return Result.error(code=404, message=f"会话不存在：{thread_id}")

    turns = []
    for row in await history.list_turns(thread_id, limit, before_seq):
        turns.append(
            TurnInfo(
                turn_id=row["turn_id"],
                thread_id=row["thread_id"],
                seq=row["seq"],
                question=row["question"],
                status=_terminal_status(row["status"]),
                created_at=row["created_at"],
                items=[TurnItemInfo(**item) for item in row["items"]],
                usage=UsageInfo(**row["usage"]) if row["usage"] else None,
            )
        )
    return Result.success(turns)
