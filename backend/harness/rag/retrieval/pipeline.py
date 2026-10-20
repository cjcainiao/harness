# 知识库检索流程

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from harness.config.app_config import get_app_config
from harness.core.logger import get_logger
from harness.rag.embedding import embed_texts
from harness.rag.retrieval.repository import base_exists, search_chunks


logger = get_logger(__name__)


async def search_knowledge(base_id: str, query: str) -> list[dict[str, Any]]:
    if not await asyncio.to_thread(base_exists, base_id):
        raise ValueError("知识库不存在")
    vector: list[float] | None = None
    try:
        vector = (await embed_texts([query]))[0]
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as error:
        logger.warning("知识库向量检索已降级为关键词检索", error=str(error))
    return await asyncio.to_thread(search_chunks, base_id, query, vector)


async def search_knowledge_many(base_id: str, queries: list[str]) -> list[dict[str, Any]]:
    if not 1 <= len(queries) <= 3:
        raise ValueError("检索问题数量必须为 1 到 3 个")
    normalized = list(dict.fromkeys(query.strip() for query in queries))
    if any(not query or len(query) > 2000 for query in normalized):
        raise ValueError("检索问题不能为空且不能超过 2000 字")
    if len(normalized) == 1:
        return await search_knowledge(base_id, normalized[0])
    if not await asyncio.to_thread(base_exists, base_id):
        raise ValueError("知识库不存在")

    config = get_app_config().rag
    vectors: list[list[float]] | None = None
    try:
        vectors = await embed_texts(normalized)
        if len(vectors) != len(normalized):
            raise ValueError("向量接口返回数量不正确")
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as error:
        logger.warning("知识库向量检索已降级为关键词检索", error=str(error))
        vectors = None

    # 每个查询保留足够候选，再合并排名
    searches = [
        asyncio.to_thread(
            search_chunks, base_id, query,
            vectors[index] if vectors is not None else None,
            limit=config.recall_top_k,
        )
        for index, query in enumerate(normalized)
    ]
    result_groups = await asyncio.gather(*searches)
    by_id: dict[int, dict[str, Any]] = {}
    scores: dict[int, float] = {}
    for group in result_groups:
        for rank, item in enumerate(group, 1):
            chunk_id = item["id"]
            by_id.setdefault(chunk_id, item)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (60 + rank)

    selected = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))[
        : config.answer_top_k
    ]
    matches: list[dict[str, Any]] = []
    for chunk_id in selected:
        item = by_id[chunk_id]
        matches.append(
            {
                **item,
                "retrieval": {
                    **item["retrieval"],
                    "rrf_score": scores[chunk_id],
                    "final_rank": len(matches) + 1,
                },
            }
        )
    return matches


