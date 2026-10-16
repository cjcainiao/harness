# 沙箱操作接口

from __future__ import annotations

from abc import ABC, abstractmethod


# 沙箱文件操作约定
class Sandbox(ABC):
    """定义沙箱中的文件操作。"""

    def __init__(self, id: str) -> None:
        self._id = id

    @property
    def id(self) -> str:
        """返回沙箱实例标识。"""
        return self._id

    @abstractmethod
    def read_file(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        """读取文本文件；行号从 1 开始，起止行均包含在结果中。"""

    @abstractmethod
    def download_file(self, path: str, *, max_bytes: int | None = None) -> bytes:
        """从沙箱取回文件原始字节，不发起网络下载；超出大小上限时抛出 OSError。"""

    @abstractmethod
    def list_dir(self, path: str) -> list[str]:
        """列出目录的第一层内容；路径不存在时抛出 FileNotFoundError。"""

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """创建或覆盖文本文件。"""

    @abstractmethod
    def update_file(self, path: str, content: bytes) -> None:
        """向沙箱写入文件的原始字节。"""

    @abstractmethod
    def delete_file(self, path: str) -> None:
        """删除单个文件，不删除目录。"""
