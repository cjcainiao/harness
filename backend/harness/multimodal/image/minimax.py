# MiniMax 图像服务

from __future__ import annotations

from harness.multimodal.image.base import ImageProvider, ImageToImageRequest, TextToImageRequest
from harness.multimodal.image.results import decode_image, response_json_object


class MiniMaxImageProvider(ImageProvider):
    generation_url = "https://api.minimaxi.com/v1/image_generation"

    async def text_to_image(self, request: TextToImageRequest) -> bytes:
        return await self._generate(request, None)

    async def image_to_image(self, request: ImageToImageRequest) -> bytes:
        return await self._generate(request, request.reference_image_data_url)

    # 参考图按 MiniMax 的人物主体参考能力传递
    async def _generate(self, request: TextToImageRequest, reference: str | None) -> bytes:
        payload = {
            "model": self.settings["model"].strip(),
            "prompt": request.prompt,
            "aspect_ratio": request.aspect_ratio,
            "response_format": "base64",
            "n": 1,
        }
        if reference is not None:
            payload["subject_reference"] = [{"type": "character", "image_file": reference}]
        response = await self.client.post(
            self.generation_url,
            headers={"Authorization": f"Bearer {self.settings['api_key'].strip()}"},
            json=payload,
        )
        body = response_json_object(response)
        base_resp = body.get("base_resp")
        if isinstance(base_resp, dict) and base_resp.get("status_code", 0) != 0:
            raise ValueError(f"图片服务请求失败：MiniMax 错误码 {base_resp['status_code']}")
        data = body.get("data")
        images = data.get("image_base64") if isinstance(data, dict) else None
        if not isinstance(images, list) or not images or not isinstance(images[0], str):
            raise ValueError("图片服务未返回图片")
        return decode_image(images[0], self.settings["max_image_bytes"])
