# 历史库表结构


# 会话表
DDL_CHAT_THREAD = """
CREATE TABLE IF NOT EXISTS chat_thread (
    -- 会话标识
    id TEXT PRIMARY KEY,
    -- 标题，默认取首条提问前 40 字，可手动修改
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

# 轮次表，一行一次提问及其完整回复
DDL_CHAT_TURN = """
CREATE TABLE IF NOT EXISTS chat_turn (
    -- 轮次标识
    id TEXT PRIMARY KEY,
    -- 所属会话标识
    thread_id TEXT NOT NULL,
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
    -- 本轮推荐的后续问题列表
    follow_up_questions_json TEXT NOT NULL DEFAULT '[]',
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

# 语句全部幂等
SCHEMA_SCRIPT = "".join(
    (
        DDL_CHAT_THREAD,
        DDL_CHAT_TURN,
        DDL_INDEX_THREAD_CREATED,
        DDL_INDEX_TURN_THREAD,
    )
)
