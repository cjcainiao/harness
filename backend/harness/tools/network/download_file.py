# 文件下载工具

from __future__ import annotations

import json
from email.message import Message
from itertools import count
from pathlib import Path
from urllib.parse import unquote

import httpx
from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, ConfigDict, Field

from harness.agents.middlewares.thread_data import workspace_path_for
from harness.tools.tool_settings import get_tool_settings


# 校验下载地址
def _download_url(value: str) -> httpx.URL:
    try:
        parsed = httpx.URL(value)
    except httpx.InvalidURL as error:
        raise ValueError(f"无效的下载地址：{value}") from error
    if parsed.scheme not in ("http", "https") or not parsed.host or parsed.username or parsed.password:
        raise ValueError(f"仅支持 HTTP/HTTPS 下载地址：{value}")
    return parsed


# 提取安全文件名
def _download_filename(response: httpx.Response, parsed: httpx.URL) -> str:
    disposition = Message()
    disposition["Content-Disposition"] = response.headers.get("content-disposition", "")
    raw_name = disposition.get_filename() or unquote(parsed.path.rsplit("/", 1)[-1]) or "download"
    name = raw_name.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join("_" if char in '<>:"/\\|?*' or ord(char) < 32 else char for char in name)
    name = name[:180].strip(" .")
    if not name:
        name = "download"
    reserved = {"CON", "PRN", "AUX", "NUL"}
    reserved.update(f"COM{index}" for index in range(1, 10))
    reserved.update(f"LPT{index}" for index in range(1, 10))
    if name.split(".", 1)[0].upper() in reserved:
        name = f"_{name}"
    return name


# 下载文件参数
class DownloadFileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, arbitrary_types_allowed=True)

    # 文件下载地址
    url: str = Field(min_length=1, description="要下载文件的 HTTP/HTTPS 地址。")

    # 当前工具运行环境
    runtime: ToolRuntime


# 下载文件到本地
@tool("download_file", args_schema=DownloadFileArgs)
def download_file(url: str, runtime: ToolRuntime) -> str:
    """从 HTTP/HTTPS 地址下载文件到当前会话的 download 目录。

    需要保存网络文件时使用。请求失败或超过大小限制时工具报错。同名文件自动使用新文件名。

    Args:
        url: 要下载文件的 HTTP/HTTPS 地址。

    Returns:
        JSON 对象字符串，含三个字段：
        - url: 最终下载地址
        - path: 当前会话 download 目录下已保存文件的绝对路径
        - bytes: 写入的字节数
    """
    # 定位当前会话工作空间
    context = runtime.context or {}
    thread_id = context.get("thread_id") or (runtime.config or {}).get("configurable", {}).get("thread_id")
    if not isinstance(thread_id, str) or not thread_id:
        raise ValueError("缺少 thread_id，无法确定下载目录")
    workspace = workspace_path_for(thread_id)
    download_dir = workspace / "download"
    if workspace.is_symlink() or download_dir.is_symlink():
        raise ValueError(f"下载目录无效：{download_dir}")
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ValueError(f"无法创建下载目录：{download_dir}") from error
    if download_dir.is_symlink():
        raise ValueError(f"下载目录无效：{download_dir}")

    # 读取下载限制
    settings = get_tool_settings("download_file")
    timeout_seconds = settings.get("timeout_seconds")
    max_download_bytes = settings.get("max_download_bytes")
    max_redirects = settings.get("max_redirects")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or timeout_seconds <= 0
    ):
        raise ValueError("download_file 的 timeout_seconds 必须大于 0")
    if isinstance(max_download_bytes, bool) or not isinstance(max_download_bytes, int) or max_download_bytes <= 0:
        raise ValueError("download_file 的 max_download_bytes 必须是正整数")
    if isinstance(max_redirects, bool) or not isinstance(max_redirects, int) or max_redirects < 0:
        raise ValueError("download_file 的 max_redirects 必须是非负整数")

    current_url = url.strip()
    target: Path | None = None
    created = False
    completed = False
    written = 0
    try:
        for redirect_count in range(max_redirects + 1):
            parsed = _download_url(current_url)

            # 限制重定向与下载大小
            try:
                with httpx.stream(
                    "GET",
                    str(parsed),
                    timeout=timeout_seconds,
                    follow_redirects=False,
                    trust_env=False,
                ) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location or redirect_count >= max_redirects:
                            raise ValueError(f"文件重定向无效或次数过多：{current_url}")
                        try:
                            current_url = str(parsed.join(location))
                        except httpx.InvalidURL as error:
                            raise ValueError(f"文件重定向地址无效：{current_url}") from error
                        continue

                    response.raise_for_status()
                    content_length = response.headers.get("content-length", "")
                    if content_length.isdigit() and int(content_length) > max_download_bytes:
                        raise ValueError(f"文件超过下载大小限制：{current_url}")

                    # 创建不覆盖的目标文件
                    filename = _download_filename(response, parsed)
                    base = Path(filename)
                    for index in count():
                        candidate = filename if index == 0 else f"{base.stem} ({index}){base.suffix}"
                        target = download_dir / candidate
                        try:
                            output = target.open("xb")
                            break
                        except FileExistsError:
                            continue
                    with output:
                        created = True
                        for chunk in response.iter_bytes():
                            if written + len(chunk) > max_download_bytes:
                                raise ValueError(f"文件超过下载大小限制：{current_url}")
                            output.write(chunk)
                            written += len(chunk)
                    completed = True
                    return json.dumps(
                        {"url": str(parsed), "path": str(target), "bytes": written},
                        ensure_ascii=False,
                    )
            except httpx.HTTPStatusError as error:
                raise ValueError(f"文件下载失败：{current_url}，HTTP {error.response.status_code}") from error
            except httpx.RequestError as error:
                raise ValueError(f"文件下载失败：{current_url}") from error
            except OSError as error:
                raise ValueError(f"文件写入失败：{target or download_dir}") from error

        raise ValueError(f"文件重定向次数过多：{url}")
    finally:
        if created and not completed and target is not None:
            target.unlink(missing_ok=True)
