# 对话消息检索接口

from fastapi import APIRouter, Query

from app.core.schemas.chat.search_schema import SearchHit
from app.core.schemas.result import Result
from app.core.services.chat.search_service import search_messages


router = APIRouter(tags=["对话检索"])


# 检索对话消息
@router.get("/search", summary="检索对话消息")
async def search_chat_messages(
    q: str = Query(min_length=1, max_length=200, description="检索关键词"),
    limit: int = Query(default=20, ge=1, le=100, description="返回条数上限"),
    before_updated_at: str | None = Query(
        default=None, max_length=32, description="游标最后活动时间，ISO-8601 UTC"
    ),
    before_thread_id: str | None = Query(
        default=None, max_length=128, description="游标会话标识，同一时刻区分先后"
    ),
) -> Result[list[SearchHit]]:
    # 游标两项必须成对，只给一项会翻出重复数据
    if (before_updated_at is None) != (before_thread_id is None):
        return Result.error(code=400, message="翻页游标需要同时给出活动时间和会话标识")

    cursor = (
        (before_updated_at, before_thread_id)
        if before_updated_at and before_thread_id
        else None
    )
    return Result.success(await search_messages(q, limit, cursor))
