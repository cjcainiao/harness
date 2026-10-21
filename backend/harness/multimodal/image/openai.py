# OpenAI 图像服务

from __future__ import annotations

import base64
import binascii
from urllib.parse import urlsplit

from harness.multimodal.image.base import ImageProvider, ImageToImageRequest, TextToImageRequest
from harness.multimodal.image.results import read_compatible_response


class OpenAIImageProvider(ImageProvider):
    generation_url = "https://api.openai.com/v1/images/generations"
    edit_url = "https://api.openai.com/v1/images/edits"
    standard_sizes = {"1:1": "1024x1024", "16:9": "1536x1024", "9:16": "1024x1536"}
    flexible_sizes = {"1:1": "1024x1024", "16:9": "1536x864", "9:16": "864x1536"}

    # 新版模型支持精确宽高比
    def _size(self, ratio: str) -> str:
        model = self.settings["model"].strip()
        sizes = self.flexible_sizes if model.startswith("gpt-image-2") else self.standard_sizes
        return sizes[ratio]

    # 兼容接口的 URL 结果仅从服务自身下载
    def _result_hosts(self) -> tuple[str, ...]:
        hostname = urlsplit(self.generation_url).hostname
        if not hostname:
            raise ValueError("图片服务地址无效")
        return (hostname,)

    async def text_to_image(self, request: TextToImageRequest) -> bytes:
        response = await self.client.post(
            self.generation_url,
            headers={"Authorization": f"Bearer {self.settings['api_key'].strip()}"},
            json={
                "model": self.settings["model"].strip(),
                "prompt": request.prompt,
                "size": self._size(request.aspect_ratio),
                "n": 1,
            },
        )
        return await read_compatible_response(self.client, response, self.settings, self._result_hosts())

    async def image_to_image(self, request: ImageToImageRequest) -> bytes:
        try:
            mime_type, encoded = request.reference_image_data_url[5:].split(";base64,", 1)
            extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[mime_type]
            image = base64.b64decode(encoded, validate=True)
        except (ValueError, KeyError, binascii.Error) as error:
            raise ValueError("参考图片编码无效") from error
        response = await self.client.post(
            self.edit_url,
            headers={"Authorization": f"Bearer {self.settings['api_key'].strip()}"},
            data={
                "model": self.settings["model"].strip(),
                "prompt": request.prompt,
                "size": self._size(request.aspect_ratio),
                "n": "1",
            },
            files={"image": (f"reference.{extension}", image, mime_type)},
        )
        return await read_compatible_response(self.client, response, self.settings, self._result_hosts())
