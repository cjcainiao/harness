# MCP 工具发现结果缓存

from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timezone

from harness.config.mcp_config import MCPConfig
from harness.mcp.loader import MCPServerDiscovery, MCPServerStatus, discover_servers


# 一次工具发现的完整结果
@dataclass(frozen=True, slots=True)
class _DiscoverySnapshot:
    signature: str
    discoveries: dict[str, MCPServerDiscovery]
    checked_at: datetime


# 对外展示的发现状态
@dataclass(frozen=True, slots=True)
class MCPStatusSnapshot:
    checked_at: datetime | None
    servers: tuple[MCPServerStatus, ...]


# 每个事件循环独立保存发现结果
@dataclass(slots=True)
class _LoopCache:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    snapshot: _DiscoverySnapshot | None = None
    generation: int = 0


_registry_lock = threading.Lock()
_loop_caches: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, _LoopCache] = weakref.WeakKeyDictionary()


# 按服务器名单与已启用服务器配置判断是否需要重新发现
def _config_signature(config: MCPConfig) -> str:
    servers = [
        (name, server.model_dump(mode="json") if server.enabled else None)
        for name, server in config.servers.items()
    ]
    encoded = json.dumps(servers, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# 获取当前事件循环的缓存
def _current_cache() -> _LoopCache:
    loop = asyncio.get_running_loop()
    with _registry_lock:
        cache = _loop_caches.get(loop)
        if cache is None:
            cache = _LoopCache()
            _loop_caches[loop] = cache
        return cache


# 发现工具并一次性替换缓存
async def _discover_and_publish(
    cache: _LoopCache, config: MCPConfig, signature: str
) -> dict[str, MCPServerDiscovery]:
    while True:
        generation = cache.generation
        discoveries = await discover_servers(config)
        with _registry_lock:
            if generation != cache.generation:
                continue
            cache.snapshot = _DiscoverySnapshot(
                signature=signature,
                discoveries=discoveries,
                checked_at=datetime.now(timezone.utc),
            )
            return discoveries


# 首次读取或配置变化时发现工具
async def get_cached_mcp_discoveries(config: MCPConfig) -> dict[str, MCPServerDiscovery]:
    cache = _current_cache()
    signature = _config_signature(config)
    snapshot = cache.snapshot
    if snapshot is not None and snapshot.signature == signature:
        return snapshot.discoveries

    async with cache.lock:
        snapshot = cache.snapshot
        if snapshot is not None and snapshot.signature == signature:
            return snapshot.discoveries
        return await _discover_and_publish(cache, config, signature)


# 只读取最近一次发现状态，不发起连接
def get_mcp_status(config: MCPConfig) -> MCPStatusSnapshot:
    snapshot = _current_cache().snapshot
    if snapshot is None or snapshot.signature != _config_signature(config):
        return MCPStatusSnapshot(
            checked_at=None,
            servers=tuple(
                MCPServerStatus(name=name, state="unchecked" if server.enabled else "disabled")
                for name, server in config.servers.items()
            ),
        )

    return MCPStatusSnapshot(
        checked_at=snapshot.checked_at,
        servers=tuple(snapshot.discoveries[name].status for name in config.servers),
    )


# 强制重新发现全部服务器，完成后更新缓存
async def refresh_mcp_discoveries(config: MCPConfig) -> MCPStatusSnapshot:
    cache = _current_cache()
    signature = _config_signature(config)
    async with cache.lock:
        await _discover_and_publish(cache, config, signature)
    return get_mcp_status(config)


# 手动清除本进程的发现结果
def reset_mcp_cache() -> None:
    with _registry_lock:
        for cache in _loop_caches.values():
            cache.generation += 1
            cache.snapshot = None
