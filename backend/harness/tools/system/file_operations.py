# 文件操作工具

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
    target = Path(path.strip()).expanduser()
    if not target.is_absolute():
        target = Path.cwd() / target
    return target.resolve()


# 列目录时跳过的噪声目录
NOISE_DIRS = {"__pycache__", "node_modules"}


# 读取文件参数
class ReadFileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 要读取的本地文件路径列表
    paths: list[str] = Field(
        min_length=1,
        description="本地文件路径列表，绝对或相对工作目录，一次可传多个",
    )

    # 起始行号
    offset: int = Field(default=1, ge=1, description="起始行号，从 1 开始；未提供时从第一行读起")

    # 单个文件的读取行数上限，未提供时用配置 settings 的默认值
    limit: int | None = Field(
        default=None,
        gt=0,
        description="每个文件最多返回的行数，没读到的行数在 remaining_lines；未提供时使用工具配置 default_max_lines",
    )


# 批量按行读取本地文件内容
@tool("read_file", args_schema=ReadFileArgs)
def read_file(paths: list[str], offset: int = 1, limit: int | None = None) -> str:
    """按行读取一个或多个本地文本文件，每行前面带行号。

    需要查看项目中文件的内容时使用，仅支持文本文件，路径必须是单个文件而非目录；一次可传多个路径，按传入顺序逐个返回；行号从 1 开始，后面的行用 offset 与 limit 续读。
    某个路径不存在、不是文本或读取失败时该项记为 error 并带上完整路径，其余文件照常返回；全部失败时工具报错。

    Args:
        paths: 本地文件路径列表，绝对或相对工作目录，一次可传多个。
        offset: 起始行号，从 1 开始；未提供时从第一行读起。
        limit: 每个文件最多返回的行数，没读到的行数在 remaining_lines；未提供时使用工具配置 default_max_lines。

    Returns:
        JSON 列表字符串，按传入顺序每项含 path（实际读取的绝对路径）、content（每行为「行号+制表符+原文」的文本）和 remaining_lines（该文件还有多少行没读取，0 表示已读完）
    """
    # 解析生效上限：模型传值优先，否则读配置
    settings = get_tool_settings("read_file")
    if "default_max_lines" not in settings:
        raise ValueError("read_file 未配置 default_max_lines")
    line_limit = limit or int(settings["default_max_lines"])

    files: list[dict[str, Any]] = []
    for path in paths:
        # 归一化为绝对路径
        target = _resolve_path(path)
        try:
            # 路径须为存在的普通文件
            if not target.is_file():
                raise ValueError(f"路径不存在或不是文件：{target}")

            with target.open("rb") as file:
                raw = file.read()

            content = _decode_text(raw)
            if content is None:
                raise ValueError(f"不是文本文件或编码不支持（utf-8/gbk）：{target}")

            # 按行取窗口，行号从 1 起
            lines = content.splitlines()
            start = offset - 1
            window = lines[start : start + line_limit]
            remaining_lines = max(len(lines) - (start + len(window)), 0)
            numbered = "\n".join(f"{number}\t{text}" for number, text in enumerate(window, start=offset))

            files.append({"path": str(target), "content": numbered, "remaining_lines": remaining_lines})
        except ValueError as error:
            # 单个文件失败只坏自己这一项，不打断整批
            files.append({"path": str(target), "error": str(error)})

    failed = [item for item in files if "error" in item]
    if len(failed) == len(files):
        raise ValueError("；".join(f"{item['path']}：{item['error']}" for item in failed))

    return json.dumps(files, ensure_ascii=False)


# 列目录参数
class ListDirArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 要列出的本地目录路径列表
    paths: list[str] = Field(
        min_length=1,
        description="本地目录路径列表，绝对或相对工作目录，一次可传多个",
    )

    # 单个目录的返回条目数上限，未提供时用配置 settings 的默认值
    max_entries: int | None = Field(
        default=None,
        gt=0,
        description="每个目录返回条目数上限，超出部分截断并在 truncated 中标记；未提供时使用工具配置 default_max_entries",
    )


# 批量列出目录下的条目
@tool("list_dir", args_schema=ListDirArgs)
def list_dir(paths: list[str], max_entries: int | None = None) -> str:
    """列出一个或多个目录下的第一层文件和子目录。

    需要查看某个目录里有哪些文件、确认路径结构时使用，一次可传多个目录路径，按传入顺序逐个返回；只列第一层不递归，隐藏条目与 __pycache__、node_modules 等噪声目录会被跳过。
    某个路径不存在、不是目录或无权访问时该项记为 error 并带上完整路径，其余目录照常返回；全部失败时工具报错。

    Args:
        paths: 本地目录路径列表，绝对或相对工作目录，一次可传多个。
        max_entries: 每个目录返回条目数上限，超出部分截断并在 truncated 中标记；未提供时使用工具配置 default_max_entries。

    Returns:
        JSON 列表字符串，按传入顺序每项含 path（实际列出的绝对路径）、entries（条目列表，每项含 name（名称）和 type（file 或 dir），目录在前按名称排序）和 truncated（条目数是否因超出 max_entries 被截断）
    """
    # 解析生效上限：模型传值优先，否则读配置
    settings = get_tool_settings("list_dir")
    if "default_max_entries" not in settings:
        raise ValueError("list_dir 未配置 default_max_entries")
    limit = max_entries or int(settings["default_max_entries"])

    listed: list[dict[str, Any]] = []
    for path in paths:
        # 归一化为绝对路径
        target = _resolve_path(path)
        try:
            # 路径须为存在的目录
            if not target.is_dir():
                raise ValueError(f"路径不存在或不是目录：{target}")

            # 跳过隐藏条目与噪声目录
            items = [item for item in target.iterdir() if not item.name.startswith(".") and item.name not in NOISE_DIRS]

            # 目录在前，同类按名称排序
            items.sort(key=lambda item: (not item.is_dir(), item.name.lower()))

            truncated = len(items) > limit
            entries = [{"name": item.name, "type": "dir" if item.is_dir() else "file"} for item in items[:limit]]

            listed.append({"path": str(target), "entries": entries, "truncated": truncated})
        except ValueError as error:
            # 单个目录失败只坏自己这一项，不打断整批
            listed.append({"path": str(target), "error": str(error)})

    failed = [item for item in listed if "error" in item]
    if len(failed) == len(listed):
        raise ValueError("；".join(f"{item['path']}：{item['error']}" for item in failed))

    return json.dumps(listed, ensure_ascii=False)


# 创建文件参数
class CreateFileArgs(BaseModel):
    # 不开 str_strip_whitespace：会连带剥掉 content 首尾空白，破坏文件内容
    model_config = ConfigDict(extra="forbid")

    # 要创建的文件路径
    path: str = Field(min_length=1, description="本地文件路径，绝对或相对工作目录，最后一段作为文件名")

    # 创建时一并写入的初始内容
    content: str = Field(default="", description="创建时写入的初始内容，传空字符串只建空文件；已有文件一律不覆盖")


# 创建本地文件
@tool("create_file", args_schema=CreateFileArgs)
def create_file(path: str, content: str = "") -> str:
    """在指定路径下创建一个本地文件，可带上初始内容。

    需要新建文件时使用，一次写入完整初始内容，空字符串即只建空文件；改已有文件的局部内容走 edit_file。
    父目录不存在、同名文件已存在或无权创建时工具报错，不自动补建目录、不覆盖已有文件，错误原因随工具结果返回。

    Args:
        path: 本地文件路径，绝对或相对工作目录，最后一段作为文件名。
        content: 创建时写入的初始内容，传空字符串只建空文件；已有文件一律不覆盖。

    Returns:
        JSON 对象字符串，含两个字段：
        - path: 已创建文件的绝对路径
        - bytes: 写入的字节数
    """
    # 归一化为绝对路径
    target = _resolve_path(path)

    # 父目录必须已存在
    if not target.parent.is_dir():
        raise ValueError(f"父目录不存在：{target.parent}")

    # 同名已存在则不覆盖
    if target.exists():
        raise ValueError(f"文件已存在，不覆盖：{target}")

    written = content.encode("utf-8")

    # 换行符按传入内容原样落盘，不做转换
    with target.open("wb") as file:
        file.write(written)

    return json.dumps({"path": str(target), "bytes": len(written)}, ensure_ascii=False)


# 编辑文件参数
class EditFileArgs(BaseModel):
    # 不开 str_strip_whitespace：会连带剥掉待替换片段首尾空白，导致匹配不上
    model_config = ConfigDict(extra="forbid")

    # 要编辑的文件路径
    path: str = Field(min_length=1, description="本地文件路径，绝对或相对工作目录，必须是已存在的文件")

    # 被替换的原片段
    old_string: str = Field(min_length=1, description="文件里被替换的原片段，需逐字照抄原文（含空格与换行）")

    # 替换后的新片段
    new_string: str = Field(description="替换后的新片段，传空字符串表示删除原片段")

    # 命中多处时是否全部替换
    allow_multiple: bool = Field(default=False, description="原片段命中多处时是否全部替换，默认 false 即命中多处直接报错")


# 替换本地文件中的一段内容
@tool("edit_file", args_schema=EditFileArgs)
def edit_file(path: str, old_string: str, new_string: str, allow_multiple: bool = False) -> str:
    """把已存在文件里的一段内容替换成另一段内容。

    需要修改文件的局部内容时使用，其余内容原样保留；新建文件走 create_file，整文件重写不支持。
    片段必须逐字照抄文件原文（含空格与换行）；文件不存在、片段找不到、命中多处又没开 allow_multiple、新旧片段相同、或文件超过 default_max_bytes 时工具报错，错误原因随工具结果返回。

    Args:
        path: 本地文件路径，绝对或相对工作目录，必须是已存在的文件。
        old_string: 文件里被替换的原片段，需逐字照抄原文（含空格与换行）。
        new_string: 替换后的新片段，传空字符串表示删除原片段。
        allow_multiple: 原片段命中多处时是否全部替换，默认 false 即命中多处直接报错。

    Returns:
        JSON 对象字符串，含两个字段：
        - path: 实际写入的绝对路径
        - replacements: 本次替换掉的片段处数
    """
    # 解析大小闸门：整文件进内存前先按字节上限拦住
    settings = get_tool_settings("edit_file")
    if "default_max_bytes" not in settings:
        raise ValueError("edit_file 未配置 default_max_bytes")
    max_bytes = int(settings["default_max_bytes"])

    # 归一化为绝对路径
    target = _resolve_path(path)

    # 只改已存在的普通文件
    if not target.is_file():
        raise ValueError(f"路径不存在或不是文件：{target}")

    size = target.stat().st_size
    if size > max_bytes:
        raise ValueError(f"文件 {size} 字节，超过上限 {max_bytes}，不做局部替换：{target}")

    if old_string == new_string:
        raise ValueError(f"old_string 与 new_string 相同：{target}")

    with target.open("rb") as file:
        raw = file.read()

    # 认原文件编码，认不出按非文本处理，回写时沿用
    encoding: str | None = None
    text = ""
    for name in ("utf-8", "gbk"):
        try:
            text = raw.decode(name)
            encoding = name
            break
        except UnicodeDecodeError:
            continue
    if encoding is None:
        raise ValueError(f"不是文本文件或编码不支持（utf-8/gbk）：{target}")

    hits = text.count(old_string)
    if hits == 0:
        raise ValueError(f"old_string 在文件里没有精确匹配，检查空格与缩进：{target}")
    if hits > 1 and not allow_multiple:
        raise ValueError(f"old_string 匹配了 {hits} 处；请增加上下文或设置 allow_multiple：{target}")

    if allow_multiple:
        new_text = text.replace(old_string, new_string)
    else:
        new_text = text.replace(old_string, new_string, 1)

    # newline 置空：按内容原样写回，不做换行符转换
    with target.open("w", encoding=encoding, newline="") as file:
        file.write(new_text)

    return json.dumps(
        {"path": str(target), "replacements": hits if allow_multiple else 1},
        ensure_ascii=False,
    )


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
