# 对话消息检索业务

from app.core.schemas.chat.search_schema import SearchHit
from harness.agents.middlewares.thread_data import workspace_path_for
from harness.storage import history


# 会话工作空间已创建时返回绝对路径
def _workspace_of(thread_id: str) -> str | None:
    path = workspace_path_for(thread_id)
    return path.as_posix() if path.is_dir() else None


# 按关键词检索会话标题、标识与轮次内容，按最后活动时间倒序
async def search_messages(
    keyword: str,
    limit: int,
    before: tuple[str, str] | None = None,
) -> list[SearchHit]:
    normalized = keyword.strip()
    if not normalized:
        return []

    rows = await history.search_threads(normalized, limit, before)
    return [
        SearchHit(
            thread_id=row["thread_id"],
            title=row["title"],
            updated_at=row["updated_at"],
            workspace=_workspace_of(row["thread_id"]),
        )
        for row in rows
    ]
