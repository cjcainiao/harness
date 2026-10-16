# 本地沙箱提供者

from __future__ import annotations

import threading
from typing import override

from harness.sandbox.local.local_sandbox import LocalSandbox
from harness.sandbox.paths import PathMapping, ensure_workspace_dir, path_mappings_for
from harness.sandbox.sandbox import Sandbox
from harness.sandbox.sandbox_provider import SandboxProvider


# 按会话管理本地沙箱
class LocalSandboxProvider(SandboxProvider):
    """创建并缓存会话沙箱，保留会话工作空间供后续对话使用。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sandboxes: dict[str, LocalSandbox] = {}
        self._mappings: dict[str, tuple[PathMapping, ...]] = {}

    # 取得当前会话的本地沙箱
    @override
    def acquire(self, thread_id: str) -> str:
        if not isinstance(thread_id, str) or not thread_id:
            raise ValueError("缺少 thread_id，无法创建会话沙箱")

        sandbox_id = f"local:{thread_id}"
        # 会话实例创建锁
        with self._lock:
            workspace = ensure_workspace_dir(thread_id)
            if workspace.is_symlink() or workspace.is_junction():
                raise ValueError(f"会话工作空间不能是链接：{workspace}")

            # 刷新技能映射
            mappings = path_mappings_for(thread_id)
            if sandbox_id not in self._sandboxes or self._mappings[sandbox_id] != mappings:
                self._sandboxes[sandbox_id] = LocalSandbox(sandbox_id, mappings)
                self._mappings[sandbox_id] = mappings
            return sandbox_id

    # 按标识查询已取得的沙箱
    @override
    def get(self, sandbox_id: str) -> Sandbox | None:
        with self._lock:
            return self._sandboxes.get(sandbox_id)

    # 本地沙箱不占用独立资源
    @override
    def release(self, sandbox_id: str) -> None:
        """保留缓存和会话文件，供下一轮对话复用。"""
