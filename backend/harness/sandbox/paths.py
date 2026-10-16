# 沙箱逻辑路径与会话目录映射

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Sequence

from harness.config.app_config import get_app_config
from harness.runtime.db_path import PROJECT_DIR
from harness.skills.loader import load_skills


# Agent 可见的用户数据根路径
VIRTUAL_PATH_PREFIX = "/mnt/user-data"

WORKSPACE_ROOT = f"{VIRTUAL_PATH_PREFIX}/workspace"
SKILLS_ROOT = "/skills"


# 单条逻辑路径映射
@dataclass(frozen=True)
class PathMapping:
    virtual_path: str
    host_path: Path
    read_only: bool


# 会话工作空间路径
def workspace_path_for(thread_id: str) -> Path:
    if not thread_id:
        raise ValueError("缺少 thread_id，无法确定会话工作空间")

    root = Path(get_app_config().system.workspace_dir)
    if not root.is_absolute():
        root = PROJECT_DIR / root

    # 会话目录哈希
    directory_name = sha256(thread_id.encode("utf-8")).hexdigest()
    return root.resolve() / directory_name


# 创建会话工作空间
def ensure_workspace_dir(thread_id: str) -> Path:
    path = workspace_path_for(thread_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


# 生成会话可见的路径映射
def path_mappings_for(thread_id: str) -> tuple[PathMapping, ...]:
    workspace = workspace_path_for(thread_id)
    mappings = [
        PathMapping(WORKSPACE_ROOT, workspace, read_only=False),
        PathMapping("/workspace", workspace, read_only=False),
    ]
    mappings.extend(
        PathMapping(f"{SKILLS_ROOT}/{skill.name}", Path(skill.path).parent, read_only=True)
        for skill in load_skills()
    )
    return tuple(mappings)


# 将沙箱逻辑路径解析为真实路径
def resolve_sandbox_path(
    path: str,
    mappings: Sequence[PathMapping],
    *,
    for_write: bool = False,
) -> Path:
    # 逻辑路径格式校验
    if not path.startswith("/") or "\\" in path or ":" in path or "\x00" in path:
        raise ValueError(f"无效的沙箱路径：{path}")

    logical_path = PurePosixPath(path)
    if ".." in logical_path.parts:
        raise ValueError(f"沙箱路径不能包含上级目录：{path}")
    if str(logical_path) != path:
        raise ValueError(f"沙箱路径格式无效：{path}")

    # 挂载路径最长匹配
    for mapping in sorted(mappings, key=lambda item: len(item.virtual_path), reverse=True):
        prefix = mapping.virtual_path
        if path != prefix and not path.startswith(f"{prefix}/"):
            continue
        # 写入权限与挂载根校验
        if for_write and mapping.read_only:
            raise PermissionError(f"沙箱路径只读：{path}")
        if mapping.host_path.is_symlink() or mapping.host_path.is_junction():
            raise ValueError(f"沙箱映射目录无效：{prefix}")

        relative = logical_path.relative_to(PurePosixPath(prefix))
        candidate = mapping.host_path
        # 拒绝链接重定向
        for part in relative.parts:
            candidate /= part
            if candidate.is_symlink() or candidate.is_junction():
                raise ValueError(f"沙箱路径包含符号链接：{path}")

        # 解析路径边界校验
        root = mapping.host_path.resolve()
        target = candidate.resolve()
        if not target.is_relative_to(root):
            raise ValueError(f"沙箱路径超出映射目录：{path}")
        return target

    # 虚拟技能根目录始终只读
    if for_write and (path == SKILLS_ROOT or path.startswith(f"{SKILLS_ROOT}/")):
        raise PermissionError(f"沙箱路径只读：{path}")
    raise ValueError(f"沙箱路径没有可用映射：{path}")
