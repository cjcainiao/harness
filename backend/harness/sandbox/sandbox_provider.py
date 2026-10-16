# 沙箱提供者接口

from __future__ import annotations

import asyncio
import importlib
import threading
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from harness.config.app_config import get_app_config
from harness.sandbox.sandbox import Sandbox


# 沙箱生命周期约定
class SandboxProvider(ABC):
    """按会话取得沙箱，并管理沙箱的本次使用。"""

    @abstractmethod
    def acquire(self, thread_id: str) -> str:
        """取得会话沙箱，返回沙箱标识。"""

    async def acquire_async(self, thread_id: str) -> str:
        """在线程中取得沙箱，避免阻塞对话的事件循环。"""
        return await asyncio.to_thread(self.acquire, thread_id)

    @abstractmethod
    def get(self, sandbox_id: str) -> Sandbox | None:
        """按标识查找已取得的沙箱，未找到时返回 None。"""

    @abstractmethod
    def release(self, sandbox_id: str) -> None:
        """释放本次占用，不删除会话工作空间中的文件。"""


# 提供者缓存锁
_provider_lock = threading.Lock()
_provider: SandboxProvider | None = None


# 按类路径加载沙箱提供者
def resolve_sandbox_provider_class(use: str) -> type[SandboxProvider]:
    module_path, separator, class_name = use.partition(":")
    if not separator or not module_path or not class_name:
        raise ValueError(f"沙箱提供者类路径格式错误：{use}，正确格式为 module:Class")

    try:
        module = importlib.import_module(module_path)
    except ImportError as error:
        raise ImportError(f"无法导入沙箱提供者模块：{module_path}") from error

    provider_class = getattr(module, class_name, None)
    if not isinstance(provider_class, type) or not issubclass(provider_class, SandboxProvider):
        raise ValueError(f"沙箱提供者类必须继承 SandboxProvider：{use}")
    return provider_class


# 懒加载提供者
def get_sandbox_provider() -> SandboxProvider:
    global _provider

    with _provider_lock:
        if _provider is not None:
            return _provider

    # 锁外构造提供者
    provider_class = resolve_sandbox_provider_class(get_app_config().sandbox.use)
    candidate = provider_class()

    # 并发实例仲裁
    with _provider_lock:
        if _provider is None:
            _provider = candidate
            return candidate
        winner = _provider

    # 释放竞争失败的实例
    shutdown = getattr(candidate, "shutdown", None)
    if callable(shutdown):
        shutdown()
    return winner


# 重置提供者缓存
def reset_sandbox_provider() -> None:
    global _provider

    with _provider_lock:
        previous = _provider
        _provider = None

    # 锁外执行清理回调
    if previous is not None:
        reset = getattr(previous, "reset", None)
        if callable(reset):
            reset()


# 本轮沙箱使用关系
class _SandboxRun:
    def __init__(self, thread_id: str) -> None:
        self.thread_id = thread_id
        # 本轮获取锁
        self._lock = threading.Lock()
        self._provider: SandboxProvider | None = None
        self._sandbox_id: str | None = None
        self._sandbox: Sandbox | None = None
        self._closed = False

    # 惰性获取沙箱
    def get(self) -> Sandbox:
        with self._lock:
            if self._closed:
                raise RuntimeError("本轮沙箱使用关系已经结束")
            if self._sandbox is not None:
                return self._sandbox

            provider = get_sandbox_provider()
            sandbox_id = provider.acquire(self.thread_id)
            sandbox = provider.get(sandbox_id)
            if sandbox is None:
                # 查找失败时释放占用
                provider.release(sandbox_id)
                raise RuntimeError(f"沙箱取得后无法查找：{sandbox_id}")

            self._provider = provider
            self._sandbox_id = sandbox_id
            self._sandbox = sandbox
            return sandbox

    # 结束本轮使用关系
    def close(self) -> None:
        # 关闭本轮状态
        with self._lock:
            if self._closed:
                return
            self._closed = True
            provider = self._provider
            sandbox_id = self._sandbox_id
            self._provider = None
            self._sandbox_id = None
            self._sandbox = None

        # 锁外释放沙箱
        if provider is not None and sandbox_id is not None:
            provider.release(sandbox_id)


# 会话运行范围
_current_run: ContextVar[_SandboxRun | None] = ContextVar("sandbox_run", default=None)


# 取得本轮会话沙箱
def get_sandbox(thread_id: str) -> Sandbox:
    # 阻止事件循环内同步获取
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise RuntimeError("异步调用请使用 aget_sandbox，避免阻塞事件循环")

    # 校验会话归属
    run = _current_run.get()
    if run is None:
        raise RuntimeError("当前没有沙箱使用范围")
    if run.thread_id != thread_id:
        raise ValueError("沙箱会话标识与本轮会话不一致")
    return run.get()


# 异步取得本轮会话沙箱
async def aget_sandbox(thread_id: str) -> Sandbox:
    return await asyncio.to_thread(get_sandbox, thread_id)


# 限定本轮沙箱使用范围
@asynccontextmanager
async def sandbox_run(thread_id: str) -> AsyncIterator[None]:
    if not isinstance(thread_id, str) or not thread_id:
        raise ValueError("缺少 thread_id，无法开启沙箱使用范围")

    # 复用同会话运行范围
    current = _current_run.get()
    if current is not None and current.thread_id == thread_id:
        yield
        return

    run = _SandboxRun(thread_id)
    token = _current_run.set(run)
    try:
        yield
    finally:
        # 退出时释放占用
        _current_run.reset(token)
        await asyncio.to_thread(run.close)
