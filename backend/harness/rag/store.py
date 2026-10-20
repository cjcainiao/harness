# 知识库数据库与文件路径

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import jieba
import sqlite_vec

from harness.config.app_config import get_app_config
from harness.rag.embedding import EMBEDDING_INPUT_FORMAT
from harness.rag.schema import DDL_FTS, SCHEMA_SCRIPT
from harness.runtime.db_path import PROJECT_DIR, resolve_db_path


def rag_db_path() -> Path:
    return resolve_db_path()


def rag_files_dir() -> Path:
    path = Path(get_app_config().rag.files_dir)
    return path if path.is_absolute() else PROJECT_DIR / path


def document_path(base_id: str, document_id: str) -> Path:
    return rag_files_dir() / base_id / document_id / "content"


def fts_tokens(text: str) -> str:
    return " ".join(jieba.cut_for_search(text))


@contextmanager
def connect_rag_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(rag_db_path())
    try:
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout = {get_app_config().system.db_busy_timeout_ms}")
        conn.enable_load_extension(True)
        try:
            sqlite_vec.load(conn)
        finally:
            conn.enable_load_extension(False)
        yield conn
    finally:
        conn.close()


def init_rag_db() -> None:
    rag_db_path().parent.mkdir(parents=True, exist_ok=True)
    rag_files_dir().mkdir(parents=True, exist_ok=True)
    config = get_app_config().rag
    if config.chunk_overlap >= config.chunk_size:
        raise ValueError("知识库切片重叠长度必须小于切片长度")
    with connect_rag_db() as conn:
        conn.executescript(SCHEMA_SCRIPT)
        expected = {
            "embedding_model": config.embedding_model,
            "embedding_dimensions": str(config.embedding_dimensions),
            "embedding_base_url": config.embedding_base_url,
            "embedding_input_format": EMBEDDING_INPUT_FORMAT,
        }
        existing = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM rag_meta")}
        vector_table = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'rag_chunk_vec'"
        ).fetchone()
        dimensions_match = (
            vector_table is not None
            and f"float[{config.embedding_dimensions}]" in vector_table[0]
        )
        if existing != expected or not dimensions_match:
            with conn:
                conn.execute("DROP TABLE IF EXISTS rag_chunk_vec")
                conn.execute("DELETE FROM rag_chunk_fts")
                conn.execute("DELETE FROM rag_chunk")
                conn.execute(
                    "UPDATE rag_document SET status = 'pending', error = NULL, chunk_count = 0, updated_at = ?",
                    (datetime.now(timezone.utc).isoformat(),),
                )
                conn.execute("DELETE FROM rag_meta")
                conn.execute(
                    f"CREATE VIRTUAL TABLE rag_chunk_vec USING vec0("
                    f"base_id text partition key, embedding float[{config.embedding_dimensions}] distance_metric=cosine)"
                )
                conn.executemany("INSERT INTO rag_meta (key, value) VALUES (?, ?)", expected.items())
        fts_columns = [row["name"] for row in conn.execute("PRAGMA table_info(rag_chunk_fts)")]
        if fts_columns != ["title", "heading", "tokens"]:
            with conn:
                conn.execute("DROP TABLE rag_chunk_fts")
                conn.execute(DDL_FTS)
                rows = conn.execute(
                    "SELECT c.id, c.heading, c.content, d.name "
                    "FROM rag_chunk c JOIN rag_document d ON d.id = c.document_id"
                )
                for row in rows:
                    conn.execute(
                        "INSERT INTO rag_chunk_fts (rowid, title, heading, tokens) VALUES (?, ?, ?, ?)",
                        (
                            row["id"],
                            fts_tokens(row["name"]),
                            fts_tokens(row["heading"]),
                            fts_tokens(row["content"]),
                        ),
                    )
        conn.execute("PRAGMA journal_mode = WAL")
        conn.commit()
