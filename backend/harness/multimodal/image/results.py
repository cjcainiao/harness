# 图像服务结果读取

from __future__ import annotations

import base64
import binascii
from collections.abc import Collection
from typing import Any, Mapping
from urllib.parse import urlsplit

import httpx


# 校验服务响应
def response_json_object(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("图片服务返回格式无效")
    return body


# 限定图片结果下载域名
def allowed_image_url(url: str, hosts: Collection[str]) -> bool:
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
def decode_image(encoded: str, max_bytes: int) -> bytes:
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
async def download_image(
    client: httpx.AsyncClient, url: str, settings: Mapping[str, Any], hosts: Collection[str]
) -> bytes:
    if not allowed_image_url(url, hosts):
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
async def read_compatible_result(
    client: httpx.AsyncClient, body: dict[str, Any], settings: Mapping[str, Any], hosts: Collection[str]
) -> bytes:
    images = body.get("data")
    if not isinstance(images, list) or not images or not isinstance(images[0], dict):
        raise ValueError("图片服务返回格式无效")
    first = images[0]
    encoded = first.get("b64_json") or first.get("image_base64") or first.get("base64")
    if isinstance(encoded, str) and encoded:
        return decode_image(encoded, settings["max_image_bytes"])
    url = first.get("url")
    if isinstance(url, str) and url.startswith("data:image/"):
        try:
            mime_type, encoded = url[5:].split(";base64,", 1)
        except ValueError as error:
            raise ValueError("图片服务返回的图片编码无效") from error
        if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise ValueError("图片服务返回的图片格式无效")
        return decode_image(encoded, settings["max_image_bytes"])
    return await download_image(client, url, settings, hosts)


# 读取兼容接口响应
async def read_compatible_response(
    client: httpx.AsyncClient,
    response: httpx.Response,
    settings: Mapping[str, Any],
    hosts: Collection[str],
) -> bytes:
    return await read_compatible_result(client, response_json_object(response), settings, hosts)
