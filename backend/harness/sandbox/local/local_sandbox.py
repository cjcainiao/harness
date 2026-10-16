# 本地文件沙箱

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from harness.sandbox.paths import SKILLS_ROOT, PathMapping, resolve_sandbox_path
from harness.sandbox.sandbox import Sandbox


# 基于路径映射的本地沙箱
class LocalSandbox(Sandbox):
    """使用逻辑路径操作本地文件；路径映射不是操作系统级隔离。"""

    def __init__(self, id: str, path_mappings: Sequence[PathMapping]) -> None:
        super().__init__(id)
        self._path_mappings = tuple(path_mappings)

    # 读取指定行范围的文本
    def read_file(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        first = 1 if start_line is None else start_line
        if type(first) is not int or first < 1:
            raise ValueError("起始行号必须是正整数")
        if end_line is not None and (type(end_line) is not int or end_line < first):
            raise ValueError("结束行号不能小于起始行号")

        target = self._resolve_file(path)
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        return "".join(lines[first - 1 : end_line])

    # 读取文件原始字节
    def download_file(self, path: str, *, max_bytes: int | None = None) -> bytes:
        if max_bytes is not None and (type(max_bytes) is not int or max_bytes < 1):
            raise ValueError("文件大小上限必须是正整数")

        target = self._resolve_file(path)
        # 超限探测字节
        with target.open("rb") as stream:
            content = stream.read() if max_bytes is None else stream.read(max_bytes + 1)
        if max_bytes is not None and len(content) > max_bytes:
            raise OSError(f"文件超过大小上限：{path}")
        return content

    # 列出目录第一层内容
    def list_dir(self, path: str) -> list[str]:
        # 虚拟技能目录
        if path == SKILLS_ROOT:
            return sorted(
                mapping.virtual_path.removeprefix(f"{SKILLS_ROOT}/").split("/", 1)[0]
                for mapping in self._path_mappings
                if mapping.virtual_path.startswith(f"{SKILLS_ROOT}/")
            )

        target = resolve_sandbox_path(path, self._path_mappings)
        if not target.exists():
            raise FileNotFoundError(f"目录不存在：{path}")
        if not target.is_dir():
            raise NotADirectoryError(f"不是目录：{path}")
        return sorted(item.name for item in target.iterdir())

    # 写入 UTF-8 文本
    def write_file(self, path: str, content: str) -> None:
        target = self._resolve_write_target(path)
        target.write_text(content, encoding="utf-8")

    # 写入文件原始字节
    def update_file(self, path: str, content: bytes) -> None:
        target = self._resolve_write_target(path)
        target.write_bytes(content)

    # 删除单个文件
    def delete_file(self, path: str) -> None:
        target = self._resolve_file(path, for_write=True)
        target.unlink()

    # 校验普通文件
    def _resolve_file(self, path: str, *, for_write: bool = False) -> Path:
        target = resolve_sandbox_path(path, self._path_mappings, for_write=for_write)
        if not target.exists():
            raise FileNotFoundError(f"文件不存在：{path}")
        if not target.is_file():
            raise IsADirectoryError(f"不是普通文件：{path}")
        return target

    # 创建写入目标的父目录
    def _resolve_write_target(self, path: str) -> Path:
        target = resolve_sandbox_path(path, self._path_mappings, for_write=True)
        if any(path == mapping.virtual_path for mapping in self._path_mappings):
            raise IsADirectoryError(f"不能将映射目录写成文件：{path}")
        if target.exists() and not target.is_file():
            raise ValueError(f"不能覆盖非普通文件：{path}")
        # 建目录后复核链接
        target.parent.mkdir(parents=True, exist_ok=True)
        return resolve_sandbox_path(path, self._path_mappings, for_write=True)
