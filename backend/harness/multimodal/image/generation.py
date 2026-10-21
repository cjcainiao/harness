# 图像生成服务统一入口

from __future__ import annotations

import json
from typing import Any, Mapping

import httpx

from harness.multimodal.image.aliyun import AliyunImageProvider
from harness.multimodal.image.apiyi import APIYIImageProvider
from harness.multimodal.image.base import ImageProvider, ImageToImageRequest, TextToImageRequest
from harness.multimodal.image.gemini import GeminiImageProvider
from harness.multimodal.image.minimax import MiniMaxImageProvider
from harness.multimodal.image.openai import OpenAIImageProvider


IMAGE_PROVIDERS: Mapping[str, type[ImageProvider]] = {
    "qwen": AliyunImageProvider,
    "apiyi": APIYIImageProvider,
    "openai": OpenAIImageProvider,
    "gemini": GeminiImageProvider,
    "minimax": MiniMaxImageProvider,
}


# 按配置选择厂商接口
async def request_image(
    prompt: str,
    ratio: str,
    settings: dict[str, Any],
    reference_image_data_url: str | None = None,
) -> bytes:
    provider_type = IMAGE_PROVIDERS.get(settings["provider"])
    if provider_type is None:
        raise ValueError("generate_image 的 provider 不受支持")
    try:
        async with httpx.AsyncClient(
            timeout=settings["timeout_seconds"], follow_redirects=False
        ) as client:
            provider = provider_type(client, settings)
            if reference_image_data_url is None:
                return await provider.text_to_image(TextToImageRequest(prompt, ratio))
            return await provider.image_to_image(
                ImageToImageRequest(prompt, ratio, reference_image_data_url)
            )
    except httpx.TimeoutException as error:
        raise ValueError("图片生成超时") from error
    except httpx.HTTPStatusError as error:
        raise ValueError(f"图片服务请求失败：HTTP {error.response.status_code}") from error
    except httpx.RequestError as error:
        raise ValueError("图片服务连接失败") from error
    except json.JSONDecodeError as error:
        raise ValueError("图片服务返回的内容不是 JSON") from error
