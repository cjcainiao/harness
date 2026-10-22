# 生成图片查询业务

from __future__ import annotations

import asyncio
from typing import Any

from harness.storage import history
from harness.tools.image.generated_files import StoredGeneratedImage, get_generated_image


# 查询会话内的生成图片
async def find_generated_image(thread_id: str, image_id: str) -> StoredGeneratedImage:
    return await asyncio.to_thread(get_generated_image, thread_id, image_id)


# 查询会话生成图片清单
async def list_thread_generated_images(thread_id: str) -> list[dict[str, Any]]:
    if await history.get_thread(thread_id) is None:
        raise LookupError(f"会话不存在：{thread_id}")
    return await history.list_generated_images(thread_id)
