# yaml 工具

from __future__ import annotations

import os
import threading
from io import StringIO
from collections.abc import Callable
from pathlib import Path
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
    with open(path, encoding="utf-8") as f:
        data = yaml.load(f)
    return data if data is not None else CommentedMap()


# 写 yaml，保留注释，原子替换
def dump_yaml(path: str | Path, data: Any) -> None:
    yaml = YAML()
    yaml.preserve_quotes = True
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    with _lock:
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        os.replace(tmp_path, path)


# 局部编辑 yaml 文本，原子替换
def edit_yaml_text(path: str | Path, edit: Callable[[str], str]) -> None:
    path = Path(path)
    tmp_path = path.with_name(path.name + ".tmp")
    with _lock:
        with open(path, encoding="utf-8", newline="") as f:
            source = f.read()
        updated = edit(source)
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            f.write(updated)
        os.replace(tmp_path, path)


# 序列化局部配置块
def render_yaml_fragment(data: Any, newline: str) -> str:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    stream = StringIO()
    yaml.dump(data, stream)
    lines = stream.getvalue().replace("\n", newline).splitlines(keepends=True)
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
