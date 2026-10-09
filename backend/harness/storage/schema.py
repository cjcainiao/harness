# 历史库表结构


# 会话表
DDL_CHAT_THREAD = """
CREATE TABLE IF NOT EXISTS chat_thread (
    -- 会话标识
    id TEXT PRIMARY KEY,
    -- 标题，取首条提问前 40 字
    title TEXT NOT NULL DEFAULT '新对话',
    -- 创建时间，ISO-8601 UTC
    created_at TEXT NOT NULL,
    -- 最后活动时间，ISO-8601 UTC
    updated_at TEXT NOT NULL,
    -- 会话累计输入 Token
    input_tokens INTEGER NOT NULL DEFAULT 0,
    -- 会话累计输出 Token
    output_tokens INTEGER NOT NULL DEFAULT 0
);
"""

# 后加的会话列，键是列名，值是补列语句
THREAD_LATE_COLUMNS = {
    "input_tokens": "ALTER TABLE chat_thread ADD COLUMN input_tokens INTEGER NOT NULL DEFAULT 0;",
    "output_tokens": "ALTER TABLE chat_thread ADD COLUMN output_tokens INTEGER NOT NULL DEFAULT 0;",
}

# 轮次表，一行一次提问及其完整回复
DDL_CHAT_TURN = """
CREATE TABLE IF NOT EXISTS chat_turn (
    -- 轮次标识
    id TEXT PRIMARY KEY,
    -- 所属会话，会话删除时级联清理
    thread_id TEXT NOT NULL REFERENCES chat_thread (id) ON DELETE CASCADE,
    -- 会话内递增序号，决定显示顺序
    seq INTEGER NOT NULL,
    -- 提问正文与附件 JSON
    question TEXT NOT NULL,
    -- 状态，取值 streaming / completed / failed / interrupted
    status TEXT NOT NULL DEFAULT 'streaming',
    -- 提问时间，ISO-8601 UTC
    created_at TEXT NOT NULL,
    -- 渲染段列表，顺序即显示顺序
    items_json TEXT NOT NULL DEFAULT '[]',
    -- 本轮累计 Token 用量
    usage_json TEXT,
    UNIQUE (thread_id, seq)
);
"""

# 会话列表按创建时间倒序翻页用
DDL_INDEX_THREAD_CREATED = """
CREATE INDEX IF NOT EXISTS idx_chat_thread_created ON chat_thread (created_at DESC, id DESC);
"""

# 按会话取历史
DDL_INDEX_TURN_THREAD = """
CREATE INDEX IF NOT EXISTS idx_chat_turn_thread ON chat_turn (thread_id, seq);
"""

# 早期的活动时间排序索引，现在不再使用
DROP_INDEX_THREAD_UPDATED = "DROP INDEX IF EXISTS idx_chat_thread_updated;"

# 启动时整段执行，语句全部幂等
SCHEMA_SCRIPT = "".join(
    (
        DDL_CHAT_THREAD,
        DDL_CHAT_TURN,
        DDL_INDEX_THREAD_CREATED,
        DDL_INDEX_TURN_THREAD,
        DROP_INDEX_THREAD_UPDATED,
    )
)
