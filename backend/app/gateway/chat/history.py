# 会话历史接口

from fastapi import APIRouter, Path, Query

from app.schemas.chat.history_schema import (
    QuestionInfo,
    ThreadInfo,
    TurnInfo,
    TurnItemInfo,
    UsageInfo,
)
from app.schemas.result import Result
from harness.storage import history


router = APIRouter(tags=["会话历史"])


# 会话列表
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


# 会话内的历史轮次
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
                question=QuestionInfo(**row["question"]),
                status=row["status"],
                created_at=row["created_at"],
                items=[TurnItemInfo(**item) for item in row["items"]],
                usage=UsageInfo(**row["usage"]) if row["usage"] else None,
            )
        )
    return Result.success(turns)
