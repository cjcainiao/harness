# yaml 工具

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


# 写锁
_lock = threading.Lock()


# 加载 yaml，返回纯 dict/list
def load_yaml(path: str | Path) -> Any:
    yaml = YAML(typ="safe")
    with open(path, encoding="utf-8") as f:
        return yaml.load(f) or {}


# 加载 yaml，保留注释
def load_yaml_keep_comment(path: str | Path) -> CommentedMap:
    yaml = YAML()
    yaml.preserve_quotes = True
    with open(path, encoding="utf-8") as f:
        data = yaml.load(f)
    return data if data is not None else CommentedMap()


# 局部编辑 yaml 文本，保留未修改内容并原子替换
def edit_yaml_text(path: str | Path, edit: Callable[[str], str]) -> None:
    path = Path(path)
    with _lock:
        with open(path, encoding="utf-8", newline="") as f:
            source = f.read()
        updated = edit(source)
        if not isinstance(updated, str):
            raise TypeError("YAML 编辑结果必须是文本")
        YAML(typ="safe").load(updated)
        if updated == source:
            return

        tmp_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                prefix=f".{path.name}.",
                suffix=".tmp",
                dir=path.parent,
                delete=False,
            ) as f:
                tmp_path = Path(f.name)
                f.write(updated)
            os.replace(tmp_path, path)
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)


# 序列化局部配置块
def render_yaml_fragment(data: Any, newline: str, mapping_indent: int = 2) -> str:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=mapping_indent, sequence=mapping_indent * 2, offset=mapping_indent)
    stream = StringIO()
    yaml.dump(data, stream)
    lines = stream.getvalue().replace("\r\n", "\n").replace("\r", "\n").replace("\n", newline).splitlines(keepends=True)
    while lines and (not lines[-1].strip() or lines[-1].lstrip().startswith("#")):
        lines.pop()
    return "".join(lines)


# 定位同级配置块末尾
def yaml_block_end(lines: list[str], start: int, indent: int) -> int:
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.strip() and not line.lstrip().startswith("#"):
            line_indent = len(line) - len(line.lstrip(" "))
            if line_indent <= indent:
                end = index
                break
    while end > start + 1 and (
        not lines[end - 1].strip() or lines[end - 1].lstrip().startswith("#")
    ):
        end -= 1
    return end
