# 会话工作空间中间件

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import override

from langchain.agents.middleware import AgentMiddleware
from langgraph.config import get_config
from langgraph.runtime import Runtime

from harness.agents.thread_state import ThreadState
from harness.config.app_config import get_app_config
from harness.runtime.db_path import PROJECT_DIR


# 根据会话标识计算安全的工作空间路径
def workspace_path_for(thread_id: str) -> Path:
    if not thread_id:
        raise ValueError("缺少 thread_id，无法确定会话工作空间")

    root = Path(get_app_config().system.workspace_dir)
    if not root.is_absolute():
        root = PROJECT_DIR / root

    # 固定长度目录名避免路径穿越、保留字符和大小写冲突
    directory_name = sha256(thread_id.encode("utf-8")).hexdigest()
    return root.resolve() / directory_name


# 首次需要写文件时创建工作空间
def ensure_workspace_dir(thread_id: str) -> Path:
    path = workspace_path_for(thread_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


# 每轮运行前写入会话工作空间路径
class ThreadDataMiddleware(AgentMiddleware[ThreadState]):
    state_schema = ThreadState

    @override
    def before_agent(self, state: ThreadState, runtime: Runtime) -> dict[str, str]:
        context = runtime.context or {}
        thread_id = context.get("thread_id") or get_config().get("configurable", {}).get("thread_id")
        if not isinstance(thread_id, str) or not thread_id:
            raise ValueError("缺少 thread_id，无法确定会话工作空间")

        return {"workspace_path": str(workspace_path_for(thread_id))}
