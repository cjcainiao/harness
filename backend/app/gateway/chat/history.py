# 会话历史接口

from fastapi import APIRouter, Path, Query

from app.exceptions import AppException
from app.schemas.chat.history_schema import ThreadInfo, ThreadTitlePatch, TurnInfo
from app.schemas.result import Result
from app.services.chat.history_service import (
    list_thread_summaries,
    list_thread_turns,
    update_thread_title,
)


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
    return Result.success(await list_thread_summaries(limit, cursor))


# 会话内的历史轮次
@router.get("/threads/{thread_id}/turns", summary="获取会话历史轮次")
async def get_thread_turns(
    thread_id: str = Path(min_length=1, max_length=128, description="会话标识"),
    limit: int = Query(default=20, ge=1, le=100, description="返回条数上限"),
    before_seq: int | None = Query(default=None, ge=1, description="游标序号，只取比它更早的轮次"),
) -> Result[list[TurnInfo]]:
    try:
        turns = await list_thread_turns(thread_id, limit, before_seq)
    except LookupError:
        return Result.error(code=404, message="会话不存在")
    return Result.success(turns)


# 修改会话标题接口
@router.patch("/threads/{thread_id}/title", summary="修改会话标题")
async def patch_thread_title(
    body: ThreadTitlePatch,
    thread_id: str = Path(min_length=1, max_length=128, description="会话标识"),
) -> Result[ThreadInfo]:
    try:
        thread = await update_thread_title(thread_id, body.title)
    except LookupError as error:
        raise AppException(code=404, message="会话不存在", status_code=404) from error
    except ValueError as error:
        raise AppException(code=422, message="会话标题无效", status_code=422) from error
    return Result.success(thread)


# 删除会话接口
@router.delete("/threads/{thread_id}", summary="删除会话")
async def delete_thread(
    thread_id: str = Path(min_length=1, max_length=128, description="会话标识"),
) -> Result[None]:
    raise NotImplementedError
