# 会话历史读写

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from harness.storage.db import connect_history_db, open_history_db


# 轮次状态，未收尾的轮次保持 streaming
TURN_STREAMING = "streaming"
TURN_COMPLETED = "completed"
TURN_FAILED = "failed"
TURN_INTERRUPTED = "interrupted"

# 会话标题取的提问字数
TITLE_MAX_CHARS = 40

# 首次提问建会话，已存在只刷新活动时间
SQL_UPSERT_THREAD = """
INSERT INTO chat_thread (id, title, created_at, updated_at)
VALUES (?, ?, ?, ?)
ON CONFLICT (id) DO UPDATE SET updated_at = excluded.updated_at
"""

# 取会话内下一个序号
SQL_NEXT_SEQ = "SELECT COALESCE(MAX(seq), 0) + 1 FROM chat_turn WHERE thread_id = ?"

# 新建轮次
SQL_INSERT_TURN = """
INSERT INTO chat_turn (id, thread_id, seq, question, status, created_at)
VALUES (?, ?, ?, ?, ?, ?)
"""

# 覆盖轮次的渲染段、用量与状态
SQL_UPDATE_TURN = """
UPDATE chat_turn
SET status = ?, items_json = ?, usage_json = ?
WHERE id = ?
"""

# 启动时把上次进程遗留的未完成轮次标为中断
SQL_INTERRUPT_UNFINISHED_TURNS = "UPDATE chat_turn SET status = ? WHERE status = ?"

# 取轮次所属会话与已落库用量，用于算增量
SQL_SELECT_TURN_USAGE = """
SELECT thread_id, usage_json
FROM chat_turn
WHERE id = ?
"""

# 会话累计 Token 按增量更新
SQL_ADD_THREAD_TOKENS = """
UPDATE chat_thread
SET input_tokens = input_tokens + ?, output_tokens = output_tokens + ?
WHERE id = ?
"""

# 会话列表，按创建时间倒序
SQL_SELECT_THREADS = """
SELECT id AS thread_id, title, created_at, updated_at, input_tokens, output_tokens
FROM chat_thread
ORDER BY created_at DESC, id DESC
LIMIT ?
"""

# 往前翻一页，同一秒内按标识打破平局
SQL_SELECT_THREADS_BEFORE = """
SELECT id AS thread_id, title, created_at, updated_at, input_tokens, output_tokens
FROM chat_thread
WHERE created_at < ? OR (created_at = ? AND id < ?)
ORDER BY created_at DESC, id DESC
LIMIT ?
"""

# 单个会话
SQL_SELECT_THREAD = """
SELECT id AS thread_id, title, created_at, updated_at, input_tokens, output_tokens
FROM chat_thread
WHERE id = ?
"""

# 会话内轮次，取最近的一页
SQL_SELECT_TURNS = """
SELECT id AS turn_id, thread_id, seq, question, status, created_at, items_json, usage_json
FROM chat_turn
WHERE thread_id = ?
ORDER BY seq DESC
LIMIT ?
"""

# 往前翻一页更早的轮次
SQL_SELECT_TURNS_BEFORE = """
SELECT id AS turn_id, thread_id, seq, question, status, created_at, items_json, usage_json
FROM chat_turn
WHERE thread_id = ? AND seq < ?
ORDER BY seq DESC
LIMIT ?
"""


# UTC 时间戳，ISO-8601 带 Z
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# 段列表转 JSON，非标准类型按字符串落库
def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


# JSON 文本还原成字典，空值按缺失处理
def _from_json(value: Any) -> dict[str, Any] | None:
    return json.loads(value) if isinstance(value, str) and value else None


# 历史提问解析
def _question_from_json(value: str) -> dict[str, Any]:
    try:
        question = json.loads(value)
    except json.JSONDecodeError:
        return {"content": value, "attachments": []}
    if (
        isinstance(question, dict)
        and isinstance(question.get("content"), str)
        and isinstance(question.get("attachments"), list)
    ):
        return {"content": question["content"], "attachments": question["attachments"]}
    return {"content": value, "attachments": []}


# 读用量计数，非法值按 0 算
def _count(usage: dict[str, Any] | None, key: str) -> int:
    value = usage.get(key) if isinstance(usage, dict) else None
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(value, 0)


# 建会话并开一轮，返回轮次标识
def start_turn(
    thread_id: str, question: str, attachments: Sequence[Mapping[str, Any]] = ()
) -> str:
    turn_id = uuid.uuid4().hex
    now = _utc_now()

    conn = connect_history_db()
    try:
        with conn:
            conn.execute(
                SQL_UPSERT_THREAD,
                (thread_id, question[:TITLE_MAX_CHARS], now, now),
            )
            seq = conn.execute(SQL_NEXT_SEQ, (thread_id,)).fetchone()[0]
            conn.execute(
                SQL_INSERT_TURN,
                (
                    turn_id,
                    thread_id,
                    seq,
                    _to_json({"content": question, "attachments": list(attachments)}),
                    TURN_STREAMING,
                    now,
                ),
            )
    finally:
        conn.close()

    return turn_id


# 进程重启后，旧的流式任务不会继续执行
def interrupt_unfinished_turns() -> None:
    conn = connect_history_db()
    try:
        with conn:
            conn.execute(
                SQL_INTERRUPT_UNFINISHED_TURNS,
                (TURN_INTERRUPTED, TURN_STREAMING),
            )
    finally:
        conn.close()


# 覆盖写入本轮进度或收尾状态，用量增量累加进会话
def update_turn(
    turn_id: str,
    status: str,
    segments: list[dict[str, Any]],
    usage: dict[str, Any] | None,
) -> None:
    conn = connect_history_db()
    try:
        with conn:
            row = conn.execute(SQL_SELECT_TURN_USAGE, (turn_id,)).fetchone()
            if row is None:
                return
            stored = _from_json(row["usage_json"])
            # 同一轮会被多次覆盖，只补本次新增的用量
            delta_input = _count(usage, "input_tokens") - _count(stored, "input_tokens")
            delta_output = _count(usage, "output_tokens") - _count(stored, "output_tokens")

            conn.execute(
                SQL_UPDATE_TURN,
                (status, _to_json(segments), _to_json(usage) if usage else None, turn_id),
            )
            if delta_input or delta_output:
                conn.execute(
                    SQL_ADD_THREAD_TOKENS,
                    (delta_input, delta_output, row["thread_id"]),
                )
    finally:
        conn.close()


# 读会话列表，before 是上一页最后一条的（创建时间, 会话标识）
async def list_threads(
    limit: int,
    before: tuple[str, str] | None = None,
) -> list[dict[str, Any]]:
    if before is None:
        sql, params = SQL_SELECT_THREADS, (limit,)
    else:
        sql = SQL_SELECT_THREADS_BEFORE
        params = (before[0], before[0], before[1], limit)

    async with open_history_db() as conn:
        async with conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# 读单个会话，不存在时返回空
async def get_thread(thread_id: str) -> dict[str, Any] | None:
    async with open_history_db() as conn:
        async with conn.execute(SQL_SELECT_THREAD, (thread_id,)) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


# 读会话轮次，按序号倒序取一页，返回时翻回正序
async def list_turns(
    thread_id: str,
    limit: int,
    before_seq: int | None = None,
) -> list[dict[str, Any]]:
    if before_seq is None:
        sql, params = SQL_SELECT_TURNS, (thread_id, limit)
    else:
        sql, params = SQL_SELECT_TURNS_BEFORE, (thread_id, before_seq, limit)

    async with open_history_db() as conn:
        async with conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

    turns: list[dict[str, Any]] = []
    for row in reversed(rows):
        turn = dict(row)
        # 历史 JSON 字段解析
        turn["question"] = _question_from_json(turn["question"])
        turn["items"] = json.loads(turn.pop("items_json"))
        usage_json = turn.pop("usage_json")
        turn["usage"] = json.loads(usage_json) if usage_json else None
        turns.append(turn)
    return turns
