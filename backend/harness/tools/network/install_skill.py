# 第三方技能安装工具

from __future__ import annotations

import ipaddress
import json
import re
import shutil
import socket
import tempfile
from email.message import Message
from pathlib import Path
from urllib.parse import quote, unquote

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from harness.config.app_config import get_app_config
from harness.skills.installer import _temp_dir, install
from harness.tools.tool_settings import get_tool_settings
from harness.utils.archive_util import compress_archive, extract_archive


_ARCHIVE_SUFFIXES = (
    ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz",
    ".tar", ".zip", ".skill", ".7z",
)
# 代理映射网段
_FAKE_DNS_RANGE = ipaddress.ip_network("198.18.0.0/15")


# 安装技能参数
class InstallSkillArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 技能来源地址
    url: str = Field(
        min_length=1,
        description="技能压缩包下载地址，或 GitHub 仓库中的技能目录链接。",
    )


# 校验公开网络地址
def _public_url(value: str) -> httpx.URL:
    try:
        parsed = httpx.URL(value)
    except httpx.InvalidURL as error:
        raise ValueError(f"技能来源地址无效：{value}") from error
    if parsed.scheme not in ("http", "https") or not parsed.host or parsed.username or parsed.password:
        raise ValueError(f"仅支持公开的 HTTP/HTTPS 技能来源地址：{value}")

    host = parsed.host.rstrip(".")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        lower_host = host.casefold()
        if lower_host == "localhost" or lower_host.endswith((".localhost", ".local", ".internal", ".home.arpa")):
            raise ValueError(f"技能来源地址不能指向本机或内网：{value}")
        try:
            records = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        except OSError as error:
            raise ValueError(f"无法解析技能来源地址：{value}") from error
        addresses = [ipaddress.ip_address(record[4][0]) for record in records]
        if not addresses or any(not (address.is_global or address in _FAKE_DNS_RANGE) for address in addresses):
            raise ValueError(f"技能来源地址不能指向本机或内网：{value}")
    else:
        if not literal.is_global:
            raise ValueError(f"技能来源地址不能指向本机或内网：{value}")
    return parsed


# 识别压缩包格式
def _archive_suffix(name: str) -> str | None:
    lower = unquote(name).casefold()
    return next((suffix for suffix in _ARCHIVE_SUFFIXES if lower.endswith(suffix)), None)


# 解析 GitHub 技能目录链接
def _github_directory(parsed: httpx.URL) -> tuple[str, tuple[str, ...]] | None:
    if parsed.host.casefold() != "github.com":
        return None
    parts = tuple(unquote(part) for part in parsed.path.strip("/").split("/"))
    if len(parts) < 3 or parts[2] != "tree":
        return None
    if len(parts) < 5:
        raise ValueError(f"GitHub 链接需要指向具体技能目录：{parsed}")
    owner, repo, _, ref, *skill_parts = parts
    for part in (owner, repo, ref, *skill_parts):
        if not part or part in {".", ".."} or "/" in part or "\\" in part or any(ord(char) < 32 for char in part):
            raise ValueError(f"GitHub 技能目录链接包含无效路径：{parsed}")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo):
        raise ValueError(f"GitHub 仓库地址无效：{parsed}")
    archive_url = f"https://github.com/{quote(owner)}/{quote(repo)}/archive/refs/heads/{quote(ref)}.zip"
    return archive_url, tuple(skill_parts)


# 下载有限大小的压缩包
def _download_archive(
    url: str,
    workdir: Path,
    *,
    suffix: str | None,
    timeout_seconds: int | float,
    max_redirects: int,
    max_download_bytes: int,
) -> Path:
    current_url = url
    with httpx.Client(timeout=timeout_seconds, follow_redirects=False, trust_env=False) as client:
        # 每次跳转重新校验地址
        for redirect_count in range(max_redirects + 1):
            parsed = _public_url(current_url)
            try:
                with client.stream("GET", str(parsed)) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location or redirect_count >= max_redirects:
                            raise ValueError(f"技能下载重定向无效或次数过多：{current_url}")
                        try:
                            current_url = str(parsed.join(location))
                        except httpx.InvalidURL as error:
                            raise ValueError(f"技能下载重定向地址无效：{current_url}") from error
                        continue

                    response.raise_for_status()
                    content_length = response.headers.get("content-length", "")
                    if content_length.isdigit() and int(content_length) > max_download_bytes:
                        raise ValueError(f"技能压缩包超过 {max_download_bytes} 字节：{current_url}")

                    disposition = Message()
                    disposition["Content-Disposition"] = response.headers.get("content-disposition", "")
                    detected = suffix or _archive_suffix(disposition.get_filename() or "") or _archive_suffix(parsed.path)
                    if detected is None:
                        raise ValueError(f"技能链接没有可识别的压缩包格式：{url}")

                    downloaded = workdir / f"download{detected}"
                    written = 0
                    with downloaded.open("xb") as output:
                        for chunk in response.iter_bytes():
                            written += len(chunk)
                            if written > max_download_bytes:
                                raise ValueError(f"技能压缩包超过 {max_download_bytes} 字节：{current_url}")
                            output.write(chunk)
                    return downloaded
            except httpx.HTTPStatusError as error:
                raise ValueError(f"技能下载失败：{current_url}，HTTP {error.response.status_code}") from error
            except httpx.RequestError as error:
                raise ValueError(f"技能下载失败：{current_url}") from error
            except OSError as error:
                raise ValueError(f"技能压缩包写入失败：{workdir}") from error
    raise ValueError(f"技能下载重定向次数过多：{url}")


# 提取指定的 GitHub 技能目录
def _github_skill_archive(downloaded: Path, workdir: Path, skill_parts: tuple[str, ...]) -> Path:
    config = get_app_config().skills
    extracted = extract_archive(
        downloaded,
        max_entries=config.max_archive_entries,
        max_unpacked_bytes=config.max_unpacked_bytes,
    )
    roots = list(extracted.iterdir())
    if len(roots) != 1 or not roots[0].is_dir():
        raise ValueError(f"GitHub 仓库压缩包结构无效：{downloaded}")
    selected = roots[0].joinpath(*skill_parts)
    if not selected.is_dir() or not (selected / config.file).is_file():
        alternatives = [
            path.parent.relative_to(roots[0]).as_posix()
            for path in roots[0].rglob(config.file)
            if path.is_file() and path.parent.name == skill_parts[-1]
        ]
        suggestion = f"；仓库中的同名目录：{', '.join(alternatives[:5])}" if alternatives else ""
        raise ValueError(f"GitHub 目录不是技能包：{'/'.join(skill_parts)}{suggestion}")

    # 只复制目标技能目录
    isolated_root = workdir / "selected"
    isolated_root.mkdir()
    isolated = isolated_root / selected.name
    shutil.copytree(selected, isolated)
    return compress_archive(isolated, "skill")


# 安装第三方技能
@tool("install_skill", args_schema=InstallSkillArgs)
def install_skill(url: str) -> str:
    """从网络地址下载并安装一个第三方技能。

    用户要安装技能时使用。支持单技能压缩包链接和 GitHub 的 tree/分支/技能目录链接；下载、压缩包或技能不合规时工具报错。

    Args:
        url: 技能压缩包下载地址，或 GitHub 仓库中的技能目录链接。

    Returns:
        JSON 对象字符串，包含四个字段：
        - name: 安装后的技能名称
        - description: 技能描述
        - path: 已安装 SKILL.md 的绝对路径
        - source_url: 本次使用的来源地址
    """
    settings = get_tool_settings("install_skill")
    timeout_seconds = settings.get("timeout_seconds")
    max_redirects = settings.get("max_redirects")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        raise ValueError("install_skill 的 timeout_seconds 必须大于 0")
    if isinstance(max_redirects, bool) or not isinstance(max_redirects, int) or max_redirects < 0:
        raise ValueError("install_skill 的 max_redirects 必须是非负整数")

    source_url = url.strip()
    parsed = _public_url(source_url)
    github = _github_directory(parsed)
    download_url = github[0] if github else source_url
    suffix = ".zip" if github else _archive_suffix(parsed.path)

    temp_root = _temp_dir()
    if temp_root.is_symlink() or temp_root.is_junction():
        raise ValueError(f"工作空间临时目录不能是链接：{temp_root}")
    try:
        temp_root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ValueError(f"无法创建工作空间临时目录：{temp_root}") from error
    with tempfile.TemporaryDirectory(prefix="install-skill-", dir=temp_root) as directory:
        workdir = Path(directory)
        downloaded = _download_archive(
            download_url,
            workdir,
            suffix=suffix,
            timeout_seconds=timeout_seconds,
            max_redirects=max_redirects,
            max_download_bytes=get_app_config().skills.max_download_bytes,
        )
        try:
            archive = _github_skill_archive(downloaded, workdir, github[1]) if github else downloaded
            skill = install(archive)
        except Exception as error:
            raise ValueError(f"技能安装失败：{source_url}：{error}") from error

    return json.dumps(
        {"name": skill.name, "description": skill.description, "path": skill.path, "source_url": source_url},
        ensure_ascii=False,
    )
