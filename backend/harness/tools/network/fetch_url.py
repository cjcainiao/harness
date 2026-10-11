# 网页内容获取工具

from __future__ import annotations

import json

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from harness.tools.tool_settings import get_tool_settings


# 校验网页地址
def _http_url(value: str) -> httpx.URL:
    try:
        parsed = httpx.URL(value)
    except httpx.InvalidURL as error:
        raise ValueError(f"无效的网页地址：{value}") from error
    if parsed.scheme not in ("http", "https") or not parsed.host or parsed.username or parsed.password:
        raise ValueError(f"仅支持 HTTP/HTTPS 网页地址：{value}")
    return parsed


# 网页获取参数
class FetchUrlArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 待获取的网页地址
    url: str = Field(min_length=1, description="待获取的网页地址。")


# 获取网页内容
@tool("fetch_url", args_schema=FetchUrlArgs)
def fetch_url(url: str) -> str:
    """获取指定网页的内容。

    需要读取网页正文时使用。网页无法获取、不是文本或超过大小限制时工具报错。

    Args:
        url: 待获取的网页地址。

    Returns:
        JSON 对象字符串，包含 url、title 和 content：
        - url: 网页地址
        - title: 网页标题
        - content: 网页正文
    """
    # 读取工具配置
    settings = get_tool_settings("fetch_url")
    timeout_seconds = settings.get("timeout_seconds")
    max_response_bytes = settings.get("max_response_bytes")
    max_content_chars = settings.get("max_content_chars")
    max_redirects = settings.get("max_redirects")
    for name, value in (
            ("timeout_seconds", timeout_seconds),
            ("max_response_bytes", max_response_bytes),
            ("max_content_chars", max_content_chars),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"fetch_url 的 {name} 必须大于 0")
    if not isinstance(max_response_bytes, int) or not isinstance(max_content_chars, int):
        raise ValueError("fetch_url 的大小限制必须是整数")
    if isinstance(max_redirects, bool) or not isinstance(max_redirects, int) or max_redirects < 0:
        raise ValueError("fetch_url 的 max_redirects 必须是非负整数")

    current_url = url.strip()
    for redirect_count in range(max_redirects + 1):
        parsed = _http_url(current_url)

        # 限制重定向与响应大小
        try:
            with httpx.stream(
                    "GET",
                    str(parsed),
                    headers={"Accept": "text/html, application/xhtml+xml, text/plain, text/markdown"},
                    timeout=timeout_seconds,
                    follow_redirects=False,
                    trust_env=False,
            ) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")
                    if not location or redirect_count >= max_redirects:
                        raise ValueError(f"网页重定向无效或次数过多：{current_url}")
                    try:
                        current_url = str(parsed.join(location))
                    except httpx.InvalidURL as error:
                        raise ValueError(f"网页重定向地址无效：{current_url}") from error
                    continue

                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if content_type not in (
                        "text/html",
                        "application/xhtml+xml",
                        "text/plain",
                        "text/markdown",
                ):
                    raise ValueError(f"网页内容不是支持的文本类型：{current_url}")
                content_length = response.headers.get("content-length", "")
                if content_length.isdigit() and int(content_length) > max_response_bytes:
                    raise ValueError(f"网页内容超过大小限制：{current_url}")

                body = bytearray()
                for chunk in response.iter_bytes():
                    if len(body) + len(chunk) > max_response_bytes:
                        raise ValueError(f"网页内容超过大小限制：{current_url}")
                    body.extend(chunk)
                encoding = response.encoding or "utf-8"
        except httpx.HTTPStatusError as error:
            raise ValueError(f"网页获取失败：{current_url}，HTTP {error.response.status_code}") from error
        except httpx.RequestError as error:
            raise ValueError(f"网页获取失败：{current_url}") from error

        # 提取网页正文
        if content_type in ("text/html", "application/xhtml+xml"):
            soup = BeautifulSoup(bytes(body), "html.parser")
            title = soup.title.get_text(" ", strip=True) if soup.title else ""
            has_external_scripts = soup.find("script", src=True) is not None
            for tag in soup(["head", "script", "style", "noscript", "template", "svg"]):
                tag.decompose()
            content = (soup.body or soup).get_text(" ", strip=True)
        else:
            title = ""
            try:
                content = body.decode(encoding, errors="replace").strip()
            except LookupError as error:
                raise ValueError(f"网页文本编码无效：{current_url}") from error
        if not content:
            if content_type in ("text/html", "application/xhtml+xml") and has_external_scripts:
                raise ValueError(f"网页没有可读取的静态正文，可能需要 JavaScript 渲染：{current_url}")
            raise ValueError(f"网页没有可读取的正文：{current_url}")
        return json.dumps(
            {"url": str(parsed), "title": title, "content": content[:max_content_chars]},
            ensure_ascii=False,
        )

    raise ValueError(f"网页重定向次数过多：{url}")
