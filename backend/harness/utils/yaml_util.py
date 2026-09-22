# yaml 工具

from __future__ import annotations

import os
import threading
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
