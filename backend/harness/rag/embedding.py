# 知识库向量生成

from __future__ import annotations

import httpx

from harness.config.app_config import get_app_config


EMBEDDING_INPUT_FORMAT = "document-heading-content"


def embedding_text(document_name: str, heading: str, content: str) -> str:
    return f"文档：{document_name}\n章节：{heading}\n内容：{content}"


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    config = get_app_config().rag
    if not config.embedding_base_url or not config.embedding_api_key:
        raise ValueError("知识库向量服务地址或密钥未配置")
    results: list[list[float]] = []
    async with httpx.AsyncClient(timeout=config.embedding_timeout_seconds) as client:
        for start in range(0, len(texts), 20):
            batch = texts[start : start + 20]
            response = await client.post(
                f"{config.embedding_base_url.rstrip('/')}/embeddings",
                headers={"Authorization": f"Bearer {config.embedding_api_key}"},
                json={"model": config.embedding_model, "input": batch, "dimensions": config.embedding_dimensions},
            )
            response.raise_for_status()
            data = response.json().get("data")
            if not isinstance(data, list) or len(data) != len(batch):
                raise ValueError("向量接口返回数量不正确")
            ordered = sorted(data, key=lambda item: item.get("index", -1))
            for item in ordered:
                vector = item.get("embedding")
                if not isinstance(vector, list) or len(vector) != config.embedding_dimensions:
                    raise ValueError("向量接口返回维度不正确")
                results.append(vector)
    return results
