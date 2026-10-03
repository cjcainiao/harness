# 库文件路径解析

from __future__ import annotations

from pathlib import Path

from harness.config.app_config import get_app_config


# 后端项目根目录，不受启动目录影响
PROJECT_DIR = Path(__file__).resolve().parents[2]


# 解析库文件绝对路径，缺省取系统配置，相对路径按后端项目根展开
def resolve_db_path(path: str | Path | None = None) -> Path:
    target = Path(path) if path is not None else Path(get_app_config().system.db_path)
    if not target.is_absolute():
        target = PROJECT_DIR / target
    return target
