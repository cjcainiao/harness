# 文档转换工具

from __future__ import annotations

import json
import os
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

from langchain.tools import ToolRuntime, tool
from markitdown import MarkItDown, StreamInfo
from pydantic import BaseModel, ConfigDict, Field

from harness.agents.middlewares.thread_data import workspace_path_for


# 当前支持的文档格式
SUPPORTED_SUFFIXES = frozenset({".docx", ".pdf"})


# 文档转 Markdown 参数
class ConvertDocumentToMarkdownArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    # 已上传附件的文件标识
    file_id: str = Field(
        min_length=1,
        description="当前会话已上传附件的 file_id，不是文件名、路径或预览地址",
    )

    # 当前工具运行环境
    runtime: ToolRuntime


# 转换当前会话的上传文档
@tool("convert_document_to_markdown", args_schema=ConvertDocumentToMarkdownArgs)
def convert_document_to_markdown(file_id: str, runtime: ToolRuntime) -> str:
    """将当前会话已上传的文档转换为 Markdown 文件。

    用户要求读取、总结或分析已上传的 DOCX、PDF 文档时使用。
    纯文本文件直接使用 read_file，图片和旧版 DOC 不适用，文档内图片不识别。
    转换后继续用 read_file 读取返回的 Markdown 路径；本工具不直接返回文档正文。附件不存在、格式不支持、
    未提取到文字或转换失败时工具报错。

    Args:
        file_id: 当前会话已上传附件的 file_id，不是文件名、路径或预览地址。

    Returns:
        JSON 对象字符串，含两个字段：
        - file_id: 被转换的附件标识
        - path: 转换后的 Markdown 本地绝对路径，可传入 read_file 的 paths 列表
    """
    # 从当前运行获取会话标识
    context = runtime.context or {}
    thread_id = context.get("thread_id") or (runtime.config or {}).get("configurable", {}).get("thread_id")
    if not isinstance(thread_id, str) or not thread_id:
        raise ValueError("缺少 thread_id，无法查找会话附件")

    # 查找当前会话的原始附件
    workspace = workspace_path_for(thread_id)
    upload_root = workspace / "uploads"
    if len(file_id) != 32 or any(char not in "0123456789abcdef" for char in file_id):
        raise ValueError(f"附件标识无效：{file_id}")
    directory = upload_root / file_id
    source = directory / "content"
    metadata_path = directory / "metadata.json"
    target = directory / "converted.md"
    if any(path.is_symlink() for path in (workspace, upload_root, directory, source, metadata_path, target)):
        raise ValueError(f"附件路径无效：{source}")
    if not source.is_file() or not metadata_path.is_file():
        raise ValueError(f"附件不存在：{source}")

    # 以存储元数据确认原文件格式
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"附件元数据无法读取：{metadata_path}") from error
    if not isinstance(metadata, dict) or metadata.get("file_id") != file_id or metadata.get("thread_id") != thread_id:
        raise ValueError(f"附件元数据无效：{metadata_path}")
    name = metadata.get("name")
    if not isinstance(name, str) or not name or Path(name).name != name:
        raise ValueError(f"附件文件名无效：{metadata_path}")
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"不支持转换此格式的文档：{source}（原文件名：{name}）")

    # 原文件以 content 存储，显式传入扩展名供转换器识别
    try:
        with source.open("rb") as stream:
            result = MarkItDown().convert_stream(
                stream,
                stream_info=StreamInfo(filename=name, extension=suffix, mimetype=metadata.get("mime_type")),
            )
    except Exception as error:
        raise ValueError(f"文档转换失败：{source}（{error}）") from error
    if not result.markdown.strip():
        raise ValueError(f"文档未提取到文字：{source}")

    # 原子写入转换结果
    temporary = directory / f".converted-{uuid4().hex}.tmp"
    try:
        temporary.write_text(result.markdown, encoding="utf-8")
        os.replace(temporary, target)
    except OSError as error:
        raise ValueError(f"Markdown 文件写入失败：{target}（{error}）") from error
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)

    return json.dumps({"file_id": file_id, "path": str(target)}, ensure_ascii=False)
