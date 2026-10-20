# 图片生成工具

from __future__ import annotations

import asyncio
import base64
import binascii
import json
from io import BytesIO
from typing import Literal
from urllib.parse import quote, urlsplit

import httpx
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field

from harness.tools.image.generated_files import save_generated_image
from harness.tools.image.view_image import load_uploaded_image
from harness.tools.tool_settings import get_tool_settings


# 图片生成参数
class GenerateImageArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    # 画面描述
    prompt: str = Field(min_length=1, description="要生成的图片内容、风格与构图描述。")

    # 图片画幅
    aspect_ratio: Literal["1:1", "16:9", "9:16"] | None = Field(
        default=None, description="图片画幅，可选 1:1、16:9 或 9:16；省略时使用系统默认画幅。"
    )

    # 当前会话的参考图片
    reference_image_id: str | None = Field(
        default=None, description="当前会话已上传图片的文件标识；仅在用户要求参考图片生成或编辑时传入。"
    )

    # 当前工具运行环境
    runtime: ToolRuntime


# 校验图片服务配置
def _settings() -> dict:
    settings = get_tool_settings("generate_image")
    required_text = ("provider", "base_url", "api_key", "model")
    for name in required_text:
        if not isinstance(settings.get(name), str) or not settings[name].strip():
            raise ValueError(f"generate_image 未配置 {name}")
    provider = settings["provider"].strip().lower()
    if provider not in {"qwen", "openai", "gemini", "minimax"}:
        raise ValueError("generate_image 的 provider 不受支持")
    base_url = settings["base_url"].strip().rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("generate_image 的 base_url 无效")
    timeout = settings.get("timeout_seconds")
    max_bytes = settings.get("max_image_bytes")
    max_pixels = settings.get("max_image_pixels")
    max_prompt = settings.get("max_prompt_chars")
    max_reference_bytes = settings.get("max_reference_image_bytes")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("generate_image 的 timeout_seconds 必须大于 0")
    for name, value in (
        ("max_image_bytes", max_bytes),
        ("max_image_pixels", max_pixels),
        ("max_prompt_chars", max_prompt),
        ("max_reference_image_bytes", max_reference_bytes),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"generate_image 的 {name} 必须是正整数")
    sizes = settings.get("sizes")
    if not isinstance(sizes, dict) or any(
        not isinstance(sizes.get(ratio), str) or not sizes[ratio]
        for ratio in ("1:1", "16:9", "9:16")
    ):
        raise ValueError("generate_image 未正确配置 sizes")
    if settings.get("default_aspect_ratio") not in sizes:
        raise ValueError("generate_image 未正确配置 default_aspect_ratio")
    hosts = settings.get("result_url_hosts")
    if not isinstance(hosts, list) or not all(isinstance(host, str) and host for host in hosts):
        raise ValueError("generate_image 未正确配置 result_url_hosts")
    return {**settings, "provider": provider, "base_url": base_url}


# 校验参考图并编码给图片服务
def _reference_image_data_url(thread_id: str, file_id: str, max_bytes: int) -> str:
    source, mime_type, data = load_uploaded_image(thread_id, file_id)
    if len(data) > max_bytes:
        raise ValueError(f"参考图片超过大小限制：{source}")
    try:
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            if width > 8000 or height > 8000 or max(width, height) > 10 * min(width, height):
                raise ValueError(f"参考图片尺寸或长宽比超出服务限制：{source}")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError(f"参考图片内容无效：{source}") from error
    return f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"


# 限定图片结果下载域名
def _allowed_image_url(url: str, hosts: list[str]) -> bool:
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https"
            and bool(hostname)
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
            and any(hostname == host.lower() or hostname.endswith("." + host.lower()) for host in hosts)
        )
    except ValueError:
        return False


# 解码图片服务返回的图片
def _decode_image(encoded: str, max_bytes: int) -> bytes:
    if len(encoded) > (max_bytes + 2) // 3 * 4 + 16:
        raise ValueError("生成图片超过大小限制")
    try:
        data = base64.b64decode(encoded, validate=True)
    except binascii.Error as error:
        raise ValueError("图片服务返回的图片编码无效") from error
    if len(data) > max_bytes:
        raise ValueError("生成图片超过大小限制")
    return data


# 下载图片服务返回的地址
async def _download_image(client: httpx.AsyncClient, url: str, settings: dict) -> bytes:
    if not _allowed_image_url(url, settings["result_url_hosts"]):
        raise ValueError("图片服务返回了未允许的图片地址")
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > settings["max_image_bytes"]:
                raise ValueError("生成图片超过大小限制")
            chunks.append(chunk)
        return b"".join(chunks)


# 读取兼容接口的图片结果
async def _openai_result(client: httpx.AsyncClient, body: dict, settings: dict) -> bytes:
    images = body.get("data")
    if not isinstance(images, list) or not images or not isinstance(images[0], dict):
        raise ValueError("图片服务返回格式无效")
    first = images[0]
    encoded = first.get("b64_json") or first.get("image_base64") or first.get("base64")
    if isinstance(encoded, str) and encoded:
        return _decode_image(encoded, settings["max_image_bytes"])
    url = first.get("url")
    if isinstance(url, str) and url.startswith("data:image/"):
        try:
            mime_type, encoded = url[5:].split(";base64,", 1)
        except ValueError as error:
            raise ValueError("图片服务返回的图片编码无效") from error
        if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise ValueError("图片服务返回的图片格式无效")
        return _decode_image(encoded, settings["max_image_bytes"])
    return await _download_image(client, url, settings)


# 请求图片服务并读取生成内容
async def _request_image(
    prompt: str, ratio: str, settings: dict, reference_image_data_url: str | None = None
) -> bytes:
    provider = settings["provider"]
    model = settings["model"].strip()
    base_url = settings["base_url"]
    try:
        async with httpx.AsyncClient(
            timeout=settings["timeout_seconds"], follow_redirects=False
        ) as client:
            if provider in {"qwen", "openai"}:
                endpoint = f"{base_url}/images/generations"
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "size": settings["sizes"][ratio],
                    "n": 1,
                }
                headers = {"Authorization": f"Bearer {settings['api_key'].strip()}"}
                if reference_image_data_url is not None and provider == "qwen":
                    payload["image"] = reference_image_data_url
                if reference_image_data_url is not None and provider == "openai":
                    encoded = reference_image_data_url.split(",", 1)[1]
                    mime_type = reference_image_data_url[5:].split(";", 1)[0]
                    extension = {
                        "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"
                    }[mime_type]
                    files = {
                        "image": (f"reference.{extension}", base64.b64decode(encoded), mime_type)
                    }
                    response = await client.post(
                        f"{base_url}/images/edits",
                        headers=headers,
                        data={
                            "model": model,
                            "prompt": prompt,
                            "size": settings["sizes"][ratio],
                            "n": "1",
                        },
                        files=files,
                    )
                else:
                    response = await client.post(endpoint, headers=headers, json=payload)
            elif provider == "gemini":
                if "/" in model or not model:
                    raise ValueError("generate_image 的 Gemini model 无效")
                parts: list[dict] = []
                if reference_image_data_url is not None:
                    mime_type, encoded = reference_image_data_url[5:].split(";base64,", 1)
                    parts.append({"inline_data": {"mime_type": mime_type, "data": encoded}})
                parts.append({"text": prompt})
                response = await client.post(
                    f"{base_url}/models/{quote(model, safe='-._')}:generateContent",
                    headers={"x-goog-api-key": settings["api_key"].strip()},
                    json={
                        "contents": [{"parts": parts}],
                        "generationConfig": {
                            "responseModalities": ["TEXT", "IMAGE"],
                            "imageConfig": {"aspectRatio": ratio},
                        },
                    },
                )
            elif provider == "minimax":
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "aspect_ratio": ratio,
                    "response_format": "base64",
                    "n": 1,
                }
                if reference_image_data_url is not None:
                    payload["subject_reference"] = [
                        {"type": "character", "image_file": reference_image_data_url}
                    ]
                response = await client.post(
                    f"{base_url}/image_generation",
                    headers={"Authorization": f"Bearer {settings['api_key'].strip()}"},
                    json=payload,
                )
            else:
                raise ValueError("generate_image 的 provider 不受支持")
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError("图片服务返回格式无效")
            if provider in {"qwen", "openai"}:
                return await _openai_result(client, body, settings)
            if provider == "gemini":
                candidates = body.get("candidates")
                if isinstance(candidates, list):
                    for candidate in candidates:
                        content = candidate.get("content") if isinstance(candidate, dict) else None
                        parts = content.get("parts") if isinstance(content, dict) else None
                        if isinstance(parts, list):
                            for part in parts:
                                if isinstance(part, dict) and part.get("thought") is True:
                                    continue
                                inline = (
                                    part.get("inlineData") or part.get("inline_data")
                                    if isinstance(part, dict)
                                    else None
                                )
                                if isinstance(inline, dict) and isinstance(inline.get("data"), str):
                                    return _decode_image(
                                        inline["data"], settings["max_image_bytes"]
                                    )
                raise ValueError("图片服务未返回图片")
            base_resp = body.get("base_resp")
            if isinstance(base_resp, dict) and base_resp.get("status_code", 0) != 0:
                raise ValueError(f"图片服务请求失败：MiniMax 错误码 {base_resp['status_code']}")
            data = body.get("data")
            images = data.get("image_base64") if isinstance(data, dict) else None
            if not isinstance(images, list) or not images or not isinstance(images[0], str):
                raise ValueError("图片服务未返回图片")
            return _decode_image(images[0], settings["max_image_bytes"])
    except httpx.TimeoutException as error:
        raise ValueError("图片生成超时") from error
    except httpx.HTTPStatusError as error:
        raise ValueError(f"图片服务请求失败：HTTP {error.response.status_code}") from error
    except httpx.RequestError as error:
        raise ValueError("图片服务连接失败") from error
    except json.JSONDecodeError as error:
        raise ValueError("图片服务返回的内容不是 JSON") from error


# 根据画面描述生成一张图片
@tool("generate_image", args_schema=GenerateImageArgs)
async def generate_image(
    prompt: str,
    runtime: ToolRuntime,
    aspect_ratio: Literal["1:1", "16:9", "9:16"] | None = None,
    reference_image_id: str | None = None,
) -> str:
    """根据文字描述生成图片，也可参考当前会话上传的图片进行编辑。

    用户明确要求画图、生成图片、参考上传图片改图时使用。参考图片无效或生成失败时工具报错。

    Args:
        prompt: 要生成的图片内容、风格与构图描述。
        aspect_ratio: 图片画幅，可选 1:1、16:9 或 9:16；省略时使用系统默认画幅。
        reference_image_id: 当前会话已上传图片的文件标识；仅在用户要求参考图片生成或编辑时传入。

    Returns:
        JSON 对象字符串，包含 image_id 图片标识、mime_type 图片格式、width 宽度和 height 高度。
    """
    context = runtime.context or {}
    thread_id = context.get("thread_id") or (runtime.config or {}).get("configurable", {}).get("thread_id")
    if not isinstance(thread_id, str) or not thread_id:
        raise ValueError("缺少 thread_id，无法保存生成图片")
    settings = _settings()
    prompt = prompt.strip()
    if not prompt or len(prompt) > settings["max_prompt_chars"]:
        raise ValueError("图片描述为空或超过长度限制")
    ratio = aspect_ratio or settings["default_aspect_ratio"]
    if ratio not in settings["sizes"]:
        raise ValueError("不支持的图片画幅")
    reference_image_data_url = None
    if reference_image_id is not None:
        reference_image_data_url = await asyncio.to_thread(
            _reference_image_data_url, thread_id, reference_image_id, settings["max_reference_image_bytes"]
        )
    data = await _request_image(prompt, ratio, settings, reference_image_data_url)
    stored = await asyncio.to_thread(
        save_generated_image,
        thread_id,
        data,
        settings["max_image_bytes"],
        settings["max_image_pixels"],
    )
    return json.dumps(
        {
            "image_id": stored.image_id,
            "mime_type": stored.mime_type,
            "width": stored.width,
            "height": stored.height,
        },
        ensure_ascii=False,
    )
