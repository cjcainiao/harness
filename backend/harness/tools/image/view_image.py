# 图片查看工具

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field

from harness.agents.middlewares.thread_data import workspace_path_for
from harness.config.app_config import get_app_config


# 可交给视觉模型的图片格式
IMAGE_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


# 根据文件头识别图片类型
def _image_mime_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


# 图片查看参数
class ViewImageArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    # 已上传图片的本地路径
    image_path: str = Field(
        min_length=1,
        description="当前会话已上传图片的本地绝对路径，来自附件清单",
    )

    # 当前工具调用标识
    tool_call_id: Annotated[str, InjectedToolCallId]

    # 当前工具运行环境
    runtime: ToolRuntime


# 查看当前会话的上传图片
@tool("view_image", args_schema=ViewImageArgs)
def view_image(
    image_path: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    runtime: ToolRuntime,
) -> Command:
    """查看当前会话已上传的图片。

    需要识别、描述或分析上传的 JPG、PNG、WebP、GIF 图片时使用。
    图片不存在、路径不属于当前会话或格式不支持时工具报错。

    Args:
        image_path: 当前会话已上传图片的本地绝对路径，来自附件清单。

    Returns:
        JSON 对象字符串，含三个字段：
        - image_path: 已查看图片的本地绝对路径
        - mime_type: 图片类型
        - size: 图片大小，单位为字节

    """
    # 获取当前会话标识
    context = runtime.context or {}
    thread_id = context.get("thread_id") or (runtime.config or {}).get("configurable", {}).get("thread_id")
    if not isinstance(thread_id, str) or not thread_id:
        raise ValueError(f"缺少 thread_id，无法查看图片：{image_path}")

    # 限定当前会话上传目录
    workspace = workspace_path_for(thread_id)
    requested = Path(image_path)
    file_id = requested.parent.name
    source = workspace / "uploads" / file_id / "content"
    metadata_path = source.parent / "metadata.json"
    if (
        not requested.is_absolute()
        or len(file_id) != 32
        or any(char not in "0123456789abcdef" for char in file_id)
        or requested != source
    ):
        raise ValueError(f"图片路径不属于当前会话上传目录：{image_path}")
    if any(path.is_symlink() for path in (workspace, workspace / "uploads", source.parent, source, metadata_path)):
        raise ValueError(f"图片路径无效：{source}")
    if not source.is_file() or not metadata_path.is_file():
        raise ValueError(f"图片不存在：{source}")

    # 校验上传元数据
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"图片元数据无法读取：{metadata_path}") from error
    if not isinstance(metadata, dict) or metadata.get("file_id") != file_id or metadata.get("thread_id") != thread_id:
        raise ValueError(f"图片元数据无效：{metadata_path}")
    name = metadata.get("name")
    if not isinstance(name, str) or not name or Path(name).name != name:
        raise ValueError(f"图片文件名无效：{metadata_path}")
    expected_mime = IMAGE_MIME_TYPES.get(Path(name).suffix.lower())
    if expected_mime is None or metadata.get("mime_type") != expected_mime:
        raise ValueError(f"不支持此格式的图片：{source}（原文件名：{name}）")

    # 读取并核对图片内容
    max_bytes = get_app_config().system.upload_max_bytes
    expected_size = metadata.get("size")
    if type(expected_size) is not int or expected_size < 1 or expected_size > max_bytes:
        raise ValueError(f"图片大小无效：{source}")
    try:
        with source.open("rb") as stream:
            image_data = stream.read(max_bytes + 1)
    except OSError as error:
        raise ValueError(f"图片无法读取：{source}") from error
    if len(image_data) != expected_size:
        raise ValueError(f"图片大小与上传记录不符：{source}")
    if _image_mime_type(image_data) != expected_mime:
        raise ValueError(f"图片内容与格式不符：{source}")

    # 记录图片元数据与本次工具结果
    image_path = source.as_posix()
    content = json.dumps(
        {"image_path": image_path, "mime_type": expected_mime, "size": expected_size},
        ensure_ascii=False,
    )
    return Command(
        update={
            "viewed_images": {
                image_path: {
                    "mime_type": expected_mime,
                    "size": expected_size,
                    "actual_path": str(source),
                    "sha256": hashlib.sha256(image_data).hexdigest(),
                }
            },
            "messages": [ToolMessage(content=content, name="view_image", tool_call_id=tool_call_id)],
        }
    )
