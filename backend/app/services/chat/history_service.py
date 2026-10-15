# 会话历史业务

import asyncio
import shutil

from fastapi import BackgroundTasks
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.schemas.chat.history_schema import (
    QuestionInfo,
    ThreadInfo,
    TurnInfo,
    TurnItemInfo,
    UsageInfo,
)
from harness.agents.memory.checkpointer import get_checkpointer
from harness.agents.middlewares.thread_data import workspace_path_for
from harness.core.logger import get_logger
from harness.storage import history


logger = get_logger(__name__)


# 查询会话摘要
async def list_thread_summaries(
    limit: int, before: tuple[str, str] | None = None
) -> list[ThreadInfo]:
    rows = await history.list_threads(limit, before)
    return [ThreadInfo(**row) for row in rows]


# 修改会话标题
async def update_thread_title(thread_id: str, title: str) -> ThreadInfo:
    normalized = title.strip()
    if not normalized:
        raise ValueError("会话标题不能为空")
    row = await asyncio.to_thread(history.update_thread_title, thread_id, normalized)
    return ThreadInfo(**row)


# 后台清理已删除会话的关联数据
def _cleanup_deleted_thread(
    thread_id: str,
    loop: asyncio.AbstractEventLoop,
    checkpointer: AsyncSqliteSaver | None,
) -> None:
    try:
        history.delete_thread_turns(thread_id)
    except Exception as error:
        logger.error("会话轮次清理失败", thread_id=thread_id, error=str(error), exc_info=True)

    if checkpointer is not None:
        try:
            future = asyncio.run_coroutine_threadsafe(checkpointer.adelete_thread(thread_id), loop)
            future.result()
        except Exception as error:
            logger.error("会话检查点清理失败", thread_id=thread_id, error=str(error), exc_info=True)

    try:
        workspace = workspace_path_for(thread_id)
        if workspace.is_symlink():
            workspace.unlink()
        elif workspace.is_dir():
            if workspace.resolve().parent != workspace.parent.resolve():
                raise ValueError(f"会话工作空间路径超出根目录：{workspace}")
            shutil.rmtree(workspace)
        elif workspace.exists():
            workspace.unlink()
    except Exception as error:
        logger.error("会话工作空间清理失败", thread_id=thread_id, error=str(error), exc_info=True)


# 删除会话主记录后交给 FastAPI 后台任务清理
async def delete_thread_data(thread_id: str, background_tasks: BackgroundTasks) -> None:
    deleted = await asyncio.to_thread(history.delete_thread_record, thread_id)
    if not deleted:
        raise LookupError(f"会话不存在：{thread_id}")

    background_tasks.add_task(
        _cleanup_deleted_thread,
        thread_id,
        asyncio.get_running_loop(),
        get_checkpointer(),
    )


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
            follow_up_questions=row["follow_up_questions"],
            usage=UsageInfo(**row["usage"]) if row["usage"] else None,
        )
        for row in rows
    ]
