# 知识库表结构

DDL_BASE = """
CREATE TABLE IF NOT EXISTS rag_base (
    -- 知识库标识
    id TEXT PRIMARY KEY,
    -- 知识库名称
    name TEXT NOT NULL,
    -- 创建时间
    created_at TEXT NOT NULL
);
"""

DDL_DOCUMENT = """
CREATE TABLE IF NOT EXISTS rag_document (
    -- 文档标识
    id TEXT PRIMARY KEY,
    -- 所属知识库
    base_id TEXT NOT NULL,
    -- 原文件名
    name TEXT NOT NULL,
    -- 内容哈希
    sha256 TEXT NOT NULL,
    -- 原文件字节数
    size INTEGER NOT NULL,
    -- 文件格式
    suffix TEXT NOT NULL,
    -- 处理状态
    status TEXT NOT NULL,
    -- 失败原因
    error TEXT,
    -- 切片数量
    chunk_count INTEGER NOT NULL DEFAULT 0,
    -- 创建时间
    created_at TEXT NOT NULL,
    -- 更新时间
    updated_at TEXT NOT NULL,
    UNIQUE (base_id, sha256)
);
"""

DDL_CHUNK = """
CREATE TABLE IF NOT EXISTS rag_chunk (
    -- 切片标识
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- 所属文档
    document_id TEXT NOT NULL,
    -- 所属知识库
    base_id TEXT NOT NULL,
    -- 文档内序号
    seq INTEGER NOT NULL,
    -- 章节标题
    heading TEXT NOT NULL,
    -- 原文内容
    content TEXT NOT NULL,
    UNIQUE (document_id, seq)
);
"""

DDL_META = """
CREATE TABLE IF NOT EXISTS rag_meta (
    -- 配置项名称
    key TEXT PRIMARY KEY,
    -- 配置项内容
    value TEXT NOT NULL
);
"""

DDL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_rag_document_base ON rag_document (base_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rag_chunk_document ON rag_chunk (document_id, seq);
"""

DDL_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunk_fts USING fts5(
    title,
    heading,
    tokens,
    tokenize='unicode61'
);
"""

SCHEMA_SCRIPT = DDL_BASE + DDL_DOCUMENT + DDL_CHUNK + DDL_META + DDL_INDEXES + DDL_FTS
