# 生成图片查询业务

from __future__ import annotations

import asyncio

from harness.tools.image.generated_files import StoredGeneratedImage, get_generated_image


# 查询会话内的生成图片
async def find_generated_image(thread_id: str, image_id: str) -> StoredGeneratedImage:
    return await asyncio.to_thread(get_generated_image, thread_id, image_id)
