# 阿里云千问图像服务

from __future__ import annotations

from harness.multimodal.image.base import ImageProvider, ImageToImageRequest, TextToImageRequest
from harness.multimodal.image.results import read_compatible_response


class AliyunImageProvider(ImageProvider):
    generation_url = (
        "https://llm-xfzs78am2mvja5bc.cn-beijing.maas.aliyuncs.com"
        "/compatible-mode/v1/images/generations"
    )
    sizes = {"1:1": "1024x1024", "16:9": "1536x864", "9:16": "864x1536"}

    async def text_to_image(self, request: TextToImageRequest) -> bytes:
        return await self._generate(request, None)

    async def image_to_image(self, request: ImageToImageRequest) -> bytes:
        return await self._generate(request, request.reference_image_data_url)

    # 千问兼容接口通过 image 字段区分两种生成方式
    async def _generate(self, request: TextToImageRequest, reference: str | None) -> bytes:
        payload = {
            "model": self.settings["model"].strip(),
            "prompt": request.prompt,
            "size": self.sizes[request.aspect_ratio],
            "n": 1,
        }
        if reference is not None:
            payload["image"] = reference
        response = await self.client.post(
            self.generation_url,
            headers={"Authorization": f"Bearer {self.settings['api_key'].strip()}"},
            json=payload,
        )
        return await read_compatible_response(self.client, response, self.settings, ("aliyuncs.com",))
