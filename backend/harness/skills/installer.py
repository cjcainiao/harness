# 技能安装器

from __future__ import annotations

from pathlib import Path

from harness.skills.loader import Skill


# 第三方技能落点目录绝对路径
def public_dir() -> Path:
    raise NotImplementedError


# 取回来源内容并落成技能包目录
def fetch(origin: str, workdir: Path) -> Path:
    raise NotImplementedError


# 安装第三方技能
def install(origin: str) -> Skill:
    raise NotImplementedError


# 卸载第三方技能
def uninstall(name: str) -> None:
    raise NotImplementedError


# 启用或停用技能
def set_enabled(name: str, enabled: bool) -> None:
    raise NotImplementedError
