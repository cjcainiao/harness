# 知识库片段检索

from __future__ import annotations

import json
from typing import Any

import jieba

from harness.config.app_config import get_app_config
from harness.rag.store import connect_rag_db


QUERY_STOPWORDS = frozenset({
    "什么", "怎么", "如何", "多少", "哪个", "哪些", "请问", "一下", "时候", "什么时候", "可以", "是否",
})


def base_exists(base_id: str) -> bool:
    with connect_rag_db() as conn:
        return conn.execute("SELECT 1 FROM rag_base WHERE id = ?", (base_id,)).fetchone() is not None


def search_chunks(
    base_id: str,
    query: str,
    vector: list[float] | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    config = get_app_config().rag
    ranks: dict[int, float] = {}
    keyword_ranks: dict[int, int] = {}
    keyword_coverage: dict[int, float] = {}
    vector_ranks: dict[int, int] = {}
    with connect_rag_db() as conn:
        terms = list(dict.fromkeys(
            term.strip().casefold()
            for term in jieba.cut_for_search(query)
            if len(term.strip()) > 1
            and any(character.isalnum() for character in term)
            and term.strip() not in QUERY_STOPWORDS
        ))[:16]
        if terms:
            match = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
            rows = conn.execute(
                "SELECT f.rowid, f.title, f.heading, f.tokens FROM rag_chunk_fts f "
                "JOIN rag_chunk c ON c.id = f.rowid "
                "JOIN rag_document d ON d.id = c.document_id "
                "WHERE rag_chunk_fts MATCH ? AND c.base_id = ? AND d.status = 'ready' "
                "ORDER BY bm25(rag_chunk_fts, 3.0, 2.0, 1.0) LIMIT ?",
                (match, base_id, config.recall_top_k),
            ).fetchall()
            for rank, row in enumerate(rows, 1):
                chunk_id = row["rowid"]
                keyword_ranks[chunk_id] = rank
                indexed_terms = set(
                    f"{row['title']} {row['heading']} {row['tokens']}".casefold().split()
                )
                keyword_coverage[chunk_id] = sum(term in indexed_terms for term in terms) / len(terms)
                ranks[chunk_id] = ranks.get(chunk_id, 0) + 1 / (60 + rank)
        if vector is not None:
            rows = conn.execute(
                "SELECT rowid, distance FROM rag_chunk_vec WHERE embedding MATCH ? AND base_id = ? AND k = ? "
                "ORDER BY distance",
                (json.dumps(vector), base_id, config.recall_top_k),
            ).fetchall()
            for rank, row in enumerate(rows, 1):
                if 1 - row["distance"] < config.min_vector_similarity:
                    continue
                chunk_id = row["rowid"]
                vector_ranks[chunk_id] = rank
                ranks[chunk_id] = ranks.get(chunk_id, 0) + 1 / (60 + rank)
        for chunk_id, coverage in keyword_coverage.items():
            if chunk_id not in vector_ranks and coverage < config.min_keyword_coverage:
                del ranks[chunk_id]
        selected = sorted(ranks, key=lambda chunk_id: (-ranks[chunk_id], chunk_id))[
            : limit if limit is not None else config.answer_top_k
        ]
        if not selected:
            return []
        placeholders = ",".join("?" for _ in selected)
        rows = conn.execute(
            "SELECT c.id, c.document_id, c.heading, c.content, d.name AS document_name "
            "FROM rag_chunk c JOIN rag_document d ON d.id = c.document_id "
            f"WHERE c.id IN ({placeholders}) AND d.status = 'ready' AND c.base_id = ?",
            (*selected, base_id),
        ).fetchall()
    by_id = {row["id"]: dict(row) for row in rows}
    matches: list[dict[str, Any]] = []
    for chunk_id in selected:
        if chunk_id not in by_id:
            continue
        matches.append({
            **by_id[chunk_id],
            "retrieval": {
                "keyword_rank": keyword_ranks.get(chunk_id),
                "vector_rank": vector_ranks.get(chunk_id),
                "rrf_score": ranks[chunk_id],
                "final_rank": len(matches) + 1,
            },
        })
    return matches
