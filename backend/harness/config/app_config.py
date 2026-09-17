# 全局配置

import logging
import os
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, Field

from harness.config.model_config import ModelConfig
from harness.config.system_config import systemConfig

logger = logging.getLogger(__name__)


# 全局配置类
class AppConfig(BaseModel):
    system: systemConfig = Field(default_factory=systemConfig, description="系统配置")
    models: list[ModelConfig] = Field(default_factory=list, description="模型配置")

    # 解析配置文件路径，优先级：参数 > 环境变量 > 默认路径
    @classmethod
    def resolve_config_path(cls, config_path: str | None = None) -> Path:
        # 1. 调用方显式指定的路径
        if config_path:
            path = Path(config_path)
            if not path.exists():
                raise FileNotFoundError(f"参数 config_path 指定的配置文件不存在：{path}")
            return path

        # 2. 环境变量 HARNESS_CONFIG_PATH
        env_path = os.getenv("HARNESS_CONFIG_PATH")
        if env_path:
            path = Path(env_path)
            if not path.exists():
                raise FileNotFoundError(f"环境变量 HARNESS_CONFIG_PATH 指定的配置文件不存在：{path}")
            return path

        # 3. 默认路径 backend/config.yaml，按本文件位置定位，不受启动目录影响
        path = Path(__file__).resolve().parents[2] / "config.yaml"
        if not path.exists():
            raise FileNotFoundError(f"默认配置文件不存在：{path}")
        return path

    # 从 YAML 文件加载配置
    @classmethod
    def from_file(cls, config_path: str | None = None) -> Self:
        resolved_path = cls.resolve_config_path(config_path)
        with open(resolved_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

        # 先校验配置版本，再解析环境变量，最后交给 pydantic 校验
        cls._check_config_version(config_data, resolved_path)
        config_data = cls.resolve_env_variables(config_data)

        # 直接映射到字段上
        return cls.model_validate(config_data)

    # 校验配置版本，低于 config.example.yaml 时告警
    @classmethod
    def _check_config_version(cls, config_data: dict, config_path: Path) -> None:
        try:
            user_version = int(config_data.get("config_version", 0))
        except (TypeError, ValueError):
            user_version = 0

        # 从 config.yaml 所在目录向上最多找 5 层 config.example.yaml
        example_path = None
        search_dir = config_path.parent
        for _ in range(5):
            candidate = search_dir / "config.example.yaml"
            if candidate.exists():
                example_path = candidate
                break
            parent = search_dir.parent
            if parent == search_dir:
                break
            search_dir = parent
        if example_path is None:
            return

        try:
            with open(example_path, encoding="utf-8") as f:
                example_data = yaml.safe_load(f)
            raw = example_data.get("config_version", 0) if example_data else 0
            try:
                example_version = int(raw)
            except (TypeError, ValueError):
                example_version = 0
        except Exception:
            return

        if user_version < example_version:
            logger.warning(
                "config.yaml 版本 %d 已过期，最新版本为 %d，请补上新增的配置项",
                user_version,
                example_version,
            )

    # 递归解析配置里的环境变量，写法 $VAR
    @classmethod
    def resolve_env_variables(cls, config: Any) -> Any:
        if isinstance(config, str):
            if config.startswith("$"):
                env_value = os.getenv(config[1:])
                if env_value is None:
                    raise ValueError(f"配置值 {config} 引用的环境变量 {config[1:]} 不存在")
                return env_value
            return config
        elif isinstance(config, dict):
            return {k: cls.resolve_env_variables(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [cls.resolve_env_variables(item) for item in config]
        return config


_app_config: AppConfig | None = None
_app_config_path: Path | None = None
_app_config_mtime: float | None = None
_app_config_is_custom = False


# 取配置文件修改时间，取不到返回 None
def _get_config_mtime(config_path: Path) -> float | None:
    try:
        return config_path.stat().st_mtime
    except OSError:
        return None


# 从磁盘加载配置并刷新缓存元数据
def _load_and_cache_app_config(config_path: str | None = None) -> AppConfig:
    global _app_config, _app_config_path, _app_config_mtime, _app_config_is_custom

    resolved_path = AppConfig.resolve_config_path(config_path)
    _app_config = AppConfig.from_file(str(resolved_path))
    _app_config_path = resolved_path
    _app_config_mtime = _get_config_mtime(resolved_path)
    _app_config_is_custom = False
    return _app_config


# 获取配置，返回缓存单例，路径或修改时间变化时自动重载
def get_app_config() -> AppConfig:
    global _app_config, _app_config_path, _app_config_mtime

    if _app_config is not None and _app_config_is_custom:
        return _app_config

    resolved_path = AppConfig.resolve_config_path()
    current_mtime = _get_config_mtime(resolved_path)

    should_reload = (
            _app_config is None
            or _app_config_path != resolved_path
            or _app_config_mtime != current_mtime
    )
    if should_reload:
        if (
                _app_config_path == resolved_path
                and _app_config_mtime is not None
                and current_mtime is not None
                and _app_config_mtime != current_mtime
        ):
            logger.info(
                "配置文件已修改（mtime: %s -> %s），重新加载 AppConfig",
                _app_config_mtime,
                current_mtime,
            )
        _load_and_cache_app_config(str(resolved_path))
    return _app_config


# 强制重新加载配置
def reload_app_config(config_path: str | None = None) -> AppConfig:
    return _load_and_cache_app_config(config_path)


# 清空配置缓存，下次 get_app_config 会重新读文件
def reset_app_config() -> None:
    global _app_config, _app_config_path, _app_config_mtime, _app_config_is_custom
    _app_config = None
    _app_config_path = None
    _app_config_mtime = None
    _app_config_is_custom = False


# 注入自定义配置，测试用
def set_app_config(config: AppConfig) -> None:
    global _app_config, _app_config_path, _app_config_mtime, _app_config_is_custom
    _app_config = config
    _app_config_path = None
    _app_config_mtime = None
    _app_config_is_custom = True
