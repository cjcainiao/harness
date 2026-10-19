# 生成图片文件存储

from __future__ import annotations

import json
import os
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from harness.agents.middlewares.thread_data import ensure_workspace_dir, workspace_path_for


# 支持的生成图片格式
IMAGE_FORMATS = {
    "PNG": ("image/png", ".png"),
    "JPEG": ("image/jpeg", ".jpg"),
    "WEBP": ("image/webp", ".webp"),
}


# 生成图片信息
@dataclass(frozen=True)
class StoredGeneratedImage:
    image_id: str
    thread_id: str
    name: str
    size: int
    mime_type: str
    width: int
    height: int
    created_at: str
    path: Path


# 校验图片标识
def _valid_image_id(image_id: str) -> bool:
    return len(image_id) == 32 and all(char in "0123456789abcdef" for char in image_id)


# 校验图片内容并读取尺寸
def _image_details(data: bytes, max_bytes: int, max_pixels: int) -> tuple[str, str, int, int]:
    if not data or len(data) > max_bytes:
        raise ValueError("生成图片为空或超过大小限制")
    try:
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
            width, height = image.size
            if image_format not in IMAGE_FORMATS or width < 1 or height < 1:
                raise ValueError("图片服务返回了不支持的图片格式")
            if width * height > max_pixels:
                raise ValueError("生成图片像素数量超过限制")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("图片服务返回的内容不是有效图片") from error
    mime_type, suffix = IMAGE_FORMATS[image_format]
    return mime_type, suffix, width, height


# 保存当前会话的生成图片
def save_generated_image(
    thread_id: str, data: bytes, max_bytes: int, max_pixels: int
) -> StoredGeneratedImage:
    mime_type, suffix, width, height = _image_details(data, max_bytes, max_pixels)
    workspace = ensure_workspace_dir(thread_id)
    root = workspace / "outputs"
    if workspace.is_symlink() or root.is_symlink():
        raise ValueError("会话图片目录无效")
    root.mkdir(parents=True, exist_ok=True)

    image_id = uuid.uuid4().hex
    directory = root / image_id
    directory.mkdir(exist_ok=False)
    content_tmp = directory / "content.tmp"
    content_path = directory / "content"
    metadata_tmp = directory / "metadata.tmp"
    metadata_path = directory / "metadata.json"
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    metadata = {
        "image_id": image_id,
        "thread_id": thread_id,
        "name": f"generated-{image_id}{suffix}",
        "size": len(data),
        "mime_type": mime_type,
        "width": width,
        "height": height,
        "created_at": created_at,
    }
    try:
        with content_tmp.open("xb") as target:
            target.write(data)
        os.replace(content_tmp, content_path)
        metadata_tmp.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        os.replace(metadata_tmp, metadata_path)
        return StoredGeneratedImage(path=content_path, **metadata)
    except Exception:
        for path in (content_tmp, content_path, metadata_tmp, metadata_path):
            with suppress(OSError):
                path.unlink(missing_ok=True)
        with suppress(OSError):
            directory.rmdir()
        raise


# 查找当前会话的生成图片
def get_generated_image(thread_id: str, image_id: str) -> StoredGeneratedImage:
    if not _valid_image_id(image_id):
        raise FileNotFoundError("生成图片不存在")
    workspace = workspace_path_for(thread_id)
    root = workspace / "outputs"
    directory = root / image_id
    content_path = directory / "content"
    metadata_path = directory / "metadata.json"
    if any(path.is_symlink() for path in (workspace, root, directory, content_path, metadata_path)):
        raise FileNotFoundError("生成图片不存在")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            not isinstance(metadata, dict)
            or metadata.get("image_id") != image_id
            or metadata.get("thread_id") != thread_id
            or metadata.get("mime_type") not in {item[0] for item in IMAGE_FORMATS.values()}
            or not isinstance(metadata.get("size"), int)
            or metadata["size"] < 1
            or content_path.stat().st_size != metadata["size"]
        ):
            raise FileNotFoundError("生成图片不存在")
        stored = StoredGeneratedImage(path=content_path, **metadata)
        if Path(stored.name).name != stored.name or stored.width < 1 or stored.height < 1:
            raise FileNotFoundError("生成图片不存在")
        return stored
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise FileNotFoundError("生成图片不存在") from error
