# 知识库文档数据访问

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from harness.rag.store import connect_rag_db, fts_tokens


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def create_base(name: str) -> dict[str, Any]:
    item = {"id": uuid4().hex, "name": name.strip(), "created_at": _now()}
    with connect_rag_db() as conn:
        conn.execute("INSERT INTO rag_base (id, name, created_at) VALUES (:id, :name, :created_at)", item)
        conn.commit()
    return item


def list_bases() -> list[dict[str, Any]]:
    with connect_rag_db() as conn:
        rows = conn.execute(
            "SELECT b.id, b.name, b.created_at, COUNT(d.id) AS document_count "
            "FROM rag_base b LEFT JOIN rag_document d ON d.base_id = b.id "
            "GROUP BY b.id ORDER BY b.created_at DESC, b.id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_base(base_id: str) -> dict[str, Any] | None:
    with connect_rag_db() as conn:
        return _row(conn.execute("SELECT * FROM rag_base WHERE id = ?", (base_id,)).fetchone())


def create_document(base_id: str, name: str, sha256: str, size: int, suffix: str) -> dict[str, Any]:
    now = _now()
    item = {
        "id": uuid4().hex,
        "base_id": base_id,
        "name": name,
        "sha256": sha256,
        "size": size,
        "suffix": suffix,
        "status": "pending",
        "error": None,
        "chunk_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    with connect_rag_db() as conn:
        if conn.execute("SELECT 1 FROM rag_base WHERE id = ?", (base_id,)).fetchone() is None:
            raise ValueError("知识库不存在")
        conn.execute(
            "INSERT INTO rag_document "
            "(id, base_id, name, sha256, size, suffix, status, error, chunk_count, created_at, updated_at) "
            "VALUES (:id, :base_id, :name, :sha256, :size, :suffix, :status, :error, "
            ":chunk_count, :created_at, :updated_at)",
            item,
        )
        conn.commit()
    return item


def list_documents(base_id: str) -> list[dict[str, Any]]:
    with connect_rag_db() as conn:
        rows = conn.execute(
            "SELECT * FROM rag_document WHERE base_id = ? ORDER BY created_at DESC, id DESC",
            (base_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_document(document_id: str) -> dict[str, Any] | None:
    with connect_rag_db() as conn:
        return _row(conn.execute("SELECT * FROM rag_document WHERE id = ?", (document_id,)).fetchone())


def pending_documents() -> list[str]:
    with connect_rag_db() as conn:
        conn.execute(
            "UPDATE rag_document SET status = 'pending', updated_at = ? "
            "WHERE status IN ('parsing', 'indexing')",
            (_now(),),
        )
        rows = conn.execute("SELECT id FROM rag_document WHERE status = 'pending'").fetchall()
        conn.commit()
    return [row["id"] for row in rows]


def set_document_status(document_id: str, status: str, error: str | None = None) -> None:
    with connect_rag_db() as conn:
        conn.execute(
            "UPDATE rag_document SET status = ?, error = ?, updated_at = ? WHERE id = ?",
            (status, error, _now(), document_id),
        )
        conn.commit()


def _delete_chunks(conn: sqlite3.Connection, document_id: str) -> None:
    ids = [
        row["id"]
        for row in conn.execute("SELECT id FROM rag_chunk WHERE document_id = ?", (document_id,))
    ]
    for chunk_id in ids:
        conn.execute("DELETE FROM rag_chunk_vec WHERE rowid = ?", (chunk_id,))
        conn.execute("DELETE FROM rag_chunk_fts WHERE rowid = ?", (chunk_id,))
    conn.execute("DELETE FROM rag_chunk WHERE document_id = ?", (document_id,))


def replace_document_chunks(document_id: str, chunks: list[dict[str, Any]], vectors: list[list[float]]) -> None:
    if len(chunks) != len(vectors):
        raise ValueError("切片和向量数量不一致")
    with connect_rag_db() as conn:
        document = conn.execute("SELECT base_id, name FROM rag_document WHERE id = ?", (document_id,)).fetchone()
        if document is None:
            raise ValueError("文档不存在")
        base_id = document["base_id"]
        title_tokens = fts_tokens(document["name"])
        with conn:
            _delete_chunks(conn, document_id)
            for seq, (chunk, vector) in enumerate(zip(chunks, vectors)):
                cursor = conn.execute(
                    "INSERT INTO rag_chunk (document_id, base_id, seq, heading, content) VALUES (?, ?, ?, ?, ?)",
                    (document_id, base_id, seq, chunk["heading"], chunk["content"]),
                )
                chunk_id = cursor.lastrowid
                conn.execute(
                    "INSERT INTO rag_chunk_fts (rowid, title, heading, tokens) VALUES (?, ?, ?, ?)",
                    (
                        chunk_id,
                        title_tokens,
                        fts_tokens(chunk["heading"]),
                        fts_tokens(chunk["content"]),
                    ),
                )
                conn.execute(
                    "INSERT INTO rag_chunk_vec (rowid, base_id, embedding) VALUES (?, ?, ?)",
                    (chunk_id, base_id, json.dumps(vector)),
                )
            conn.execute(
                "UPDATE rag_document SET status = 'ready', error = NULL, chunk_count = ?, updated_at = ? WHERE id = ?",
                (len(chunks), _now(), document_id),
            )


def delete_document(document_id: str) -> dict[str, Any] | None:
    with connect_rag_db() as conn:
        row = conn.execute("SELECT * FROM rag_document WHERE id = ?", (document_id,)).fetchone()
        if row is None:
            return None
        with conn:
            _delete_chunks(conn, document_id)
            conn.execute("DELETE FROM rag_document WHERE id = ?", (document_id,))
        return dict(row)


def delete_base(base_id: str) -> bool:
    with connect_rag_db() as conn:
        if conn.execute("SELECT 1 FROM rag_base WHERE id = ?", (base_id,)).fetchone() is None:
            return False
        document_ids = [
            row["id"] for row in conn.execute("SELECT id FROM rag_document WHERE base_id = ?", (base_id,))
        ]
        with conn:
            for document_id in document_ids:
                _delete_chunks(conn, document_id)
            conn.execute("DELETE FROM rag_document WHERE base_id = ?", (base_id,))
            conn.execute("DELETE FROM rag_base WHERE id = ?", (base_id,))
        return True


def list_chunks(document_id: str) -> list[dict[str, Any]]:
    with connect_rag_db() as conn:
        rows = conn.execute(
            "SELECT id, seq, heading, content FROM rag_chunk WHERE document_id = ? ORDER BY seq",
            (document_id,),
        ).fetchall()
    return [dict(row) for row in rows]
