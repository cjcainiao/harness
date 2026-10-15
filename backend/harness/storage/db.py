# 历史库连接

from __future__ import annotations

import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from harness.config.app_config import get_app_config
from harness.runtime.db_path import resolve_db_path
from harness.storage.schema import SCHEMA_SCRIPT


# 每个连接都设置数据库等待时间
def session_pragmas() -> tuple[str, ...]:
    timeout = get_app_config().system.db_busy_timeout_ms
    return (f"PRAGMA busy_timeout = {timeout}",)


# 打开同步连接，写库用短事务
def connect_history_db(path: str | Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(resolve_db_path(path))
    conn.row_factory = sqlite3.Row
    for pragma in session_pragmas():
        conn.execute(pragma)
    return conn


# 打开历史库连接
@asynccontextmanager
async def open_history_db(path: str | Path | None = None) -> AsyncIterator[aiosqlite.Connection]:
    conn = await aiosqlite.connect(resolve_db_path(path))
    try:
        conn.row_factory = aiosqlite.Row
        for pragma in session_pragmas():
            await conn.execute(pragma)
        yield conn
    finally:
        await conn.close()


# 建目录并执行建表脚本，语句幂等
async def init_history_db(path: str | Path | None = None) -> Path:
    db_path = resolve_db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(db_path)
    try:
        await conn.executescript(SCHEMA_SCRIPT)
        # WAL 是库级持久属性，重复设置无副作用
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.commit()
    finally:
        await conn.close()

    return db_path
