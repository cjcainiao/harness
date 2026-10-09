# 上传文件校验与存储

from __future__ import annotations

import json
import mimetypes
import os
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote

from harness.agents.middlewares.thread_data import ensure_workspace_dir, workspace_path_for
from harness.config.app_config import get_app_config


# 允许上传的文件类型
ALLOWED_SUFFIXES = frozenset(
    """
    jpg jpeg png gif webp bmp svg ico heic heif tif tiff
    pdf doc docx xls xlsx xlsb ppt pptx epub rtf csv txt log md markdown mdx
    json json5 yaml yml toml xml ini conf env html htm css scss less
    js mjs cjs jsx ts tsx vue py ipynb go java kt swift rs c h cpp hpp
    cs rb php dart lua sql sh bash zsh bat cmd ps1
    """.split()
)
ALLOWED_NAMES = frozenset(
    {"dockerfile", "makefile", "readme", "license", "jenkinsfile", "gitignore", "editorconfig"}
)
INLINE_IMAGE_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
)
CHUNK_SIZE = 1024 * 1024


# 上传业务错误
class UploadStoreError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.status_code = status_code
        super().__init__(message)


# 附件存储信息
@dataclass(frozen=True)
class StoredUpload:
    file_id: str
    thread_id: str
    name: str
    size: int
    mime_type: str
    created_at: str
    path: Path


# 附件预览地址
def upload_preview_url(thread_id: str, file_id: str) -> str:
    prefix = get_app_config().system.api_prefix.rstrip("/")
    return f"{prefix}/uploads/{file_id}/preview?thread_id={quote(thread_id, safe='')}"


# 文件名校验
def _file_name(filename: str | None) -> tuple[str, str]:
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name or len(name) > 255 or any(ord(char) < 32 for char in name):
        raise UploadStoreError("文件名无效")
    lowered = name.lower()
    suffix = lowered.rsplit(".", 1)[-1]
    if lowered not in ALLOWED_NAMES and suffix not in ALLOWED_SUFFIXES:
        raise UploadStoreError(f"不支持上传此类型的文件：{name}")
    return name, suffix


# 图片文件头校验
def _valid_image_header(suffix: str, header: bytes) -> bool:
    if suffix == "png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {"jpg", "jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if suffix == "gif":
        return header.startswith((b"GIF87a", b"GIF89a"))
    if suffix == "webp":
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    if suffix == "bmp":
        return header.startswith(b"BM")
    return True


# 会话上传目录
def _upload_root(thread_id: str, *, create: bool) -> Path:
    workspace = ensure_workspace_dir(thread_id) if create else workspace_path_for(thread_id)
    root = workspace / "uploads"
    if workspace.is_symlink() or root.is_symlink():
        raise UploadStoreError("会话上传目录无效")
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


# 附件目录
def _upload_dir(thread_id: str, file_id: str) -> Path:
    if len(file_id) != 32 or any(char not in "0123456789abcdef" for char in file_id):
        raise UploadStoreError("附件不存在", 404)
    directory = _upload_root(thread_id, create=False) / file_id
    if directory.is_symlink():
        raise UploadStoreError("附件不存在", 404)
    return directory


# 文件与元数据保存
def save_upload(thread_id: str, filename: str | None, source: BinaryIO) -> StoredUpload:
    name, suffix = _file_name(filename)
    max_bytes = get_app_config().system.upload_max_bytes
    file_id = uuid.uuid4().hex
    directory = _upload_root(thread_id, create=True) / file_id
    directory.mkdir(exist_ok=False)
    content_tmp = directory / "content.tmp"
    content_path = directory / "content"
    metadata_tmp = directory / "metadata.tmp"
    metadata_path = directory / "metadata.json"

    try:
        size = 0
        header = b""
        with content_tmp.open("xb") as target:
            while chunk := source.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise UploadStoreError(f"文件超过 {max_bytes} 字节上限", 413)
                if not header:
                    header = chunk[:16]
                target.write(chunk)
        if size == 0:
            raise UploadStoreError("不能上传空文件")
        if not _valid_image_header(suffix, header):
            raise UploadStoreError("图片内容与文件类型不符")

        mime_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        metadata = {
            "file_id": file_id,
            "thread_id": thread_id,
            "name": name,
            "size": size,
            "mime_type": mime_type,
            "created_at": created_at,
        }
        os.replace(content_tmp, content_path)
        metadata_tmp.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        os.replace(metadata_tmp, metadata_path)
        return StoredUpload(path=content_path, **metadata)
    except Exception:
        for path in (content_tmp, content_path, metadata_tmp, metadata_path):
            with suppress(OSError):
                path.unlink(missing_ok=True)
        with suppress(OSError):
            directory.rmdir()
        raise


# 会话附件查找
def get_upload(thread_id: str, file_id: str) -> StoredUpload:
    directory = _upload_dir(thread_id, file_id)
    metadata_path = directory / "metadata.json"
    content_path = directory / "content"
    if metadata_path.is_symlink() or content_path.is_symlink():
        raise UploadStoreError("附件不存在", 404)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise UploadStoreError("附件不存在", 404) from error
    if (
        not isinstance(metadata, dict)
        or metadata.get("file_id") != file_id
        or metadata.get("thread_id") != thread_id
        or not content_path.is_file()
    ):
        raise UploadStoreError("附件不存在", 404)
    try:
        return StoredUpload(path=content_path, **metadata)
    except TypeError as error:
        raise UploadStoreError("附件不存在", 404) from error


# 会话附件删除
def delete_upload(thread_id: str, file_id: str) -> None:
    stored = get_upload(thread_id, file_id)
    stored.path.unlink()
    (stored.path.parent / "metadata.json").unlink()
    stored.path.parent.rmdir()
