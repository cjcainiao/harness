# 代理检查点记忆

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from harness.config.app_config import get_app_config
from harness.runtime.db_path import resolve_db_path

# 进程内持有的检查点器与它的库连接
_checkpointer: AsyncSqliteSaver | None = None
_conn: aiosqlite.Connection | None = None


# 建连接并初始化检查点表
async def init_checkpointer() -> AsyncSqliteSaver | None:
    global _checkpointer, _conn

    config = get_app_config()
    memory = config.memory
    if not memory.enabled:
        return None

    target = resolve_db_path(memory.db_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(target)
    try:
        await conn.execute(f"PRAGMA busy_timeout = {config.system.db_busy_timeout_ms}")
        # WAL 是库级持久属性，重复设置无副作用
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.commit()

        checkpointer = AsyncSqliteSaver(conn)
        # 建表语句幂等，每次启动都能跑
        await checkpointer.setup()
    except Exception:
        # 初始化失败时放掉连接，免得库文件一直被占
        await conn.close()
        raise

    _conn = conn
    _checkpointer = checkpointer
    return checkpointer


# 取当前检查点器
def get_checkpointer() -> AsyncSqliteSaver | None:
    return _checkpointer


# 关闭连接，释放库文件占用
async def shutdown_checkpointer() -> None:
    global _checkpointer, _conn

    conn = _conn
    _checkpointer = None
    _conn = None
    if conn is not None:
        await conn.close()
