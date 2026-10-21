# 图像服务统一接口

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping

import httpx


@dataclass(frozen=True, slots=True)
class TextToImageRequest:
    prompt: str
    aspect_ratio: str


@dataclass(frozen=True, slots=True)
class ImageToImageRequest(TextToImageRequest):
    reference_image_data_url: str


class ImageProvider(ABC):
    def __init__(self, client: httpx.AsyncClient, settings: Mapping[str, Any]) -> None:
        self.client = client
        self.settings = settings

    @abstractmethod
    async def text_to_image(self, request: TextToImageRequest) -> bytes:
        """按文字描述生成图片。"""

    @abstractmethod
    async def image_to_image(self, request: ImageToImageRequest) -> bytes:
        """按参考图片和文字描述生成图片。"""
