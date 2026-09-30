# 文件操作工具

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from harness.tools.tool_settings import get_tool_settings


# 按候选编码依次解码文本，全部失败返回 None
def _decode_text(raw: bytes) -> str | None:
    for encoding in ("utf-8", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


# 归一化为绝对路径
def _resolve_path(path: str) -> Path:
    target = Path(path).expanduser()
    if not target.is_absolute():
        target = Path.cwd() / target
    return target.resolve()


# 列目录时跳过的噪声目录
NOISE_DIRS = {"__pycache__", "node_modules"}


# 读取文件参数
class ReadFileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 要读取的本地文件路径
    path: str = Field(min_length=1, description="本地文件路径，绝对或相对工作目录")

    # 读取字节上限，未提供时用配置 settings 的默认值
    max_bytes: int | None = Field(
        default=None,
        gt=0,
        description="读取的字节上限，超出部分截断并在 truncated 中标记；未提供时使用工具配置 default_max_bytes",
    )


# 读取本地文件内容
@tool("read_file", args_schema=ReadFileArgs)
def read_file(path: str, max_bytes: int | None = None) -> str:
    """读取本地文本文件的内容。

    需要查看项目中某个文件的内容时使用，仅支持文本文件，路径必须是单个文件而非目录。
    文件不存在、不是文本或读取失败时工具报错，错误原因随工具结果返回。

    Args:
        path: 本地文件路径，绝对或相对工作目录。
        max_bytes: 读取的字节上限，超出部分截断并在 truncated 中标记；未提供时使用工具配置 default_max_bytes。

    Returns:
        JSON 对象字符串，含三个字段：
        - path: 实际读取的绝对路径
        - content: 文件内容
        - truncated: 内容是否因超出 max_bytes 被截断
    """
    # 解析生效上限：模型传值优先，否则读配置
    settings = get_tool_settings("read_file")
    if "default_max_bytes" not in settings:
        raise ValueError("read_file 未配置 default_max_bytes")
    limit = max_bytes or int(settings["default_max_bytes"])

    # 归一化为绝对路径
    target = _resolve_path(path)

    # 路径须为存在的普通文件
    if not target.is_file():
        raise ValueError(f"路径不存在或不是文件：{target}")

    # 多读 1 字节用于判断是否截断
    with target.open("rb") as file:
        raw = file.read(limit + 1)

    truncated = len(raw) > limit
    raw = raw[:limit]

    # 截断可能切断多字节字符，末尾忽略残缺字节再试
    content = _decode_text(raw)
    if content is None and truncated:
        content = raw.decode("utf-8", errors="ignore")
    if content is None:
        raise ValueError(f"不是文本文件或编码不支持（utf-8/gbk）：{target}")

    return json.dumps(
        {"path": str(target), "content": content, "truncated": truncated},
        ensure_ascii=False,
    )


# 列目录参数
class ListDirArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 要列出的目录路径
    path: str = Field(min_length=1, description="本地目录路径，绝对或相对工作目录")

    # 返回条目数上限，未提供时用配置 settings 的默认值
    max_entries: int | None = Field(
        default=None,
        gt=0,
        description="返回条目数上限，超出部分截断并在 truncated 中标记；未提供时使用工具配置 default_max_entries",
    )


# 列出目录下的条目
@tool("list_dir", args_schema=ListDirArgs)
def list_dir(path: str, max_entries: int | None = None) -> str:
    """列出目录下第一层的文件和子目录。

    需要查看某个目录里有哪些文件、确认路径结构时使用，只列第一层不递归，隐藏条目与 __pycache__、node_modules 等噪声目录会被跳过。
    路径不存在、不是目录或无权访问时工具报错，错误原因随工具结果返回。

    Args:
        path: 本地目录路径，绝对或相对工作目录。
        max_entries: 返回条目数上限，超出部分截断并在 truncated 中标记；未提供时使用工具配置 default_max_entries。

    Returns:
        JSON 对象字符串，含三个字段：
        - path: 实际列出的绝对路径
        - entries: 条目列表，每项含 name（名称）和 type（file 或 dir），目录在前按名称排序
        - truncated: 条目数是否因超出 max_entries 被截断
    """
    # 解析生效上限：模型传值优先，否则读配置
    settings = get_tool_settings("list_dir")
    if "default_max_entries" not in settings:
        raise ValueError("list_dir 未配置 default_max_entries")
    limit = max_entries or int(settings["default_max_entries"])

    # 归一化为绝对路径
    target = _resolve_path(path)

    # 路径须为存在的目录
    if not target.is_dir():
        raise ValueError(f"路径不存在或不是目录：{target}")

    # 跳过隐藏条目与噪声目录
    items = [item for item in target.iterdir() if not item.name.startswith(".") and item.name not in NOISE_DIRS]

    # 目录在前，同类按名称排序
    items.sort(key=lambda item: (not item.is_dir(), item.name.lower()))

    truncated = len(items) > limit
    entries = [{"name": item.name, "type": "dir" if item.is_dir() else "file"} for item in items[:limit]]

    return json.dumps(
        {"path": str(target), "entries": entries, "truncated": truncated},
        ensure_ascii=False,
    )


# 编辑文件参数
class EditFileArgs(BaseModel):
    # 不开 str_strip_whitespace：会连带剥掉 content 首尾空白，破坏文件内容
    model_config = ConfigDict(extra="forbid")

    # 要写入的文件路径
    path: str = Field(min_length=1, description="本地文件路径，绝对或相对工作目录；不存在时创建，存在时整文件覆盖")

    # 写入的完整文本内容
    content: str = Field(description="写入的完整文本内容，覆盖原文件全部内容；清空文件传空字符串")


# 创建或覆盖本地文件
@tool("edit_file", args_schema=EditFileArgs)
def edit_file(path: str, content: str) -> str:
    """按完整内容创建或覆盖一个本地文本文件。

    需要新建文件或对已有文件整体改写时使用；父目录不存在会自动创建。
    只写文本内容，路径指向目录时工具报错，错误原因随工具结果返回。

    Args:
        path: 本地文件路径，绝对或相对工作目录；不存在时创建，存在时整文件覆盖。
        content: 写入的完整文本内容，覆盖原文件全部内容；清空文件传空字符串。

    Returns:
        JSON 对象字符串，含两个字段：
        - path: 实际写入的绝对路径
        - created: 是否新建，false 表示覆盖了已有文件
    """
    # 归一化为绝对路径
    target = _resolve_path(path)

    if target.is_dir():
        raise ValueError(f"路径是目录，不能按文件写入：{target}")

    created = not target.exists()

    # 补建父目录
    target.parent.mkdir(parents=True, exist_ok=True)

    # newline 置空：按内容原样写入，不做换行符转换
    with target.open("w", encoding="utf-8", newline="") as file:
        file.write(content)

    return json.dumps({"path": str(target), "created": created}, ensure_ascii=False)


# 删除文件参数
class DeleteFileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 要删除的文件路径
    path: str = Field(min_length=1, description="本地文件路径，绝对或相对工作目录，只能是单个文件")


# 删除本地文件
@tool("delete_file", args_schema=DeleteFileArgs)
def delete_file(path: str) -> str:
    """删除一个本地文件。

    确认需要移除某个文件时使用；只删单个文件，不删目录、不递归、不支持通配符，删除后不可恢复。
    路径不存在、是目录或无权删除时工具报错，错误原因随工具结果返回。

    Args:
        path: 本地文件路径，绝对或相对工作目录，只能是单个文件。

    Returns:
        JSON 对象字符串，含一个字段：
        - path: 已删除文件的绝对路径
    """
    # 归一化为绝对路径
    target = _resolve_path(path)

    # 只删存在的普通文件
    if not target.is_file():
        raise ValueError(f"路径不存在或不是文件：{target}")

    target.unlink()

    return json.dumps({"path": str(target)}, ensure_ascii=False)
