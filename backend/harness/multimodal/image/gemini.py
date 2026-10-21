# 谷歌 Gemini 图像服务

from __future__ import annotations

from urllib.parse import quote

from harness.multimodal.image.base import ImageProvider, ImageToImageRequest, TextToImageRequest
from harness.multimodal.image.results import decode_image, response_json_object


class GeminiImageProvider(ImageProvider):
    generation_url = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    async def text_to_image(self, request: TextToImageRequest) -> bytes:
        return await self._generate(request, None)

    async def image_to_image(self, request: ImageToImageRequest) -> bytes:
        return await self._generate(request, request.reference_image_data_url)

    async def _generate(self, request: TextToImageRequest, reference: str | None) -> bytes:
        model = self.settings["model"].strip()
        if "/" in model or not model:
            raise ValueError("generate_image 的 Gemini model 无效")
        parts: list[dict] = []
        if reference is not None:
            try:
                mime_type, encoded = reference[5:].split(";base64,", 1)
            except ValueError as error:
                raise ValueError("参考图片编码无效") from error
            parts.append({"inline_data": {"mime_type": mime_type, "data": encoded}})
        parts.append({"text": request.prompt})
        response = await self.client.post(
            self.generation_url.format(model=quote(model, safe="-._")),
            headers={"x-goog-api-key": self.settings["api_key"].strip()},
            json={
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"],
                    "imageConfig": {"aspectRatio": request.aspect_ratio},
                },
            },
        )
        body = response_json_object(response)
        candidates = body.get("candidates")
        if isinstance(candidates, list):
            for candidate in candidates:
                content = candidate.get("content") if isinstance(candidate, dict) else None
                parts = content.get("parts") if isinstance(content, dict) else None
                if isinstance(parts, list):
                    for part in parts:
                        if not isinstance(part, dict) or part.get("thought") is True:
                            continue
                        inline = part.get("inlineData") or part.get("inline_data")
                        if isinstance(inline, dict) and isinstance(inline.get("data"), str):
                            return decode_image(inline["data"], self.settings["max_image_bytes"])
        raise ValueError("图片服务未返回图片")
