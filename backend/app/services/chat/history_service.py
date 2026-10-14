# 会话历史业务

from app.schemas.chat.history_schema import (
    QuestionInfo,
    ThreadInfo,
    TurnInfo,
    TurnItemInfo,
    UsageInfo,
)
from harness.storage import history


# 查询会话摘要
async def list_thread_summaries(
    limit: int, before: tuple[str, str] | None = None
) -> list[ThreadInfo]:
    rows = await history.list_threads(limit, before)
    return [ThreadInfo(**row) for row in rows]


# 查询会话轮次
async def list_thread_turns(
    thread_id: str, limit: int, before_seq: int | None = None
) -> list[TurnInfo]:
    if await history.get_thread(thread_id) is None:
        raise LookupError(f"会话不存在：{thread_id}")

    rows = await history.list_turns(thread_id, limit, before_seq)
    return [
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
        for row in rows
    ]
