# 模型工厂

import importlib
from typing import Any, Literal

from langchain.chat_models import BaseChatModel

from harness.config.app_config import AppConfig, get_app_config
from harness.config.model_config import ModelConfig


ReasoningEffort = Literal["low", "medium", "high"]

_MODEL_METADATA_FIELDS = {
    "name", # 模型配置名称
    "display_name", # 模型显示名称
    "description", # 模型描述
    "use", # 模型实现类路径
    "supports_thinking", # 是否支持推理
    "supports_reasoning_effort", # 是否支持推理程度
    "when_thinking_enabled", # 启用推理时追加的参数
    "when_thinking_disabled", # 关闭推理时追加的参数
    "supports_vision", # 是否支持视觉
    "context_window", # 模型上下文长度
}


# 根据类路径动态加载模型实现类
def resolve_model_class(class_path: str) -> type[BaseChatModel]:
    module_path, separator, class_name = class_path.partition(":")
    if not separator or not module_path or not class_name:
        raise ValueError(f"模型实现类路径格式错误：{class_path}，正确格式为 module:Class")

    try:
        module = importlib.import_module(module_path)
    except ImportError as error:
        raise ImportError(f"无法导入模型模块：{module_path}") from error

    try:
        model_class = getattr(module, class_name)
    except AttributeError as error:
        raise ImportError(f"模型模块 {module_path} 中不存在类：{class_name}") from error

    if not isinstance(model_class, type) or not issubclass(model_class, BaseChatModel):
        raise ValueError(f"模型实现类必须继承 BaseChatModel：{class_path}")
    return model_class


# 根据名称获取模型配置，第一个模型为默认模型
def _get_model_config(config: AppConfig, name: str | None) -> ModelConfig:
    if not config.models:
        raise ValueError("未配置任何模型")

    if name is None:
        return config.models[0]

    model_config = next((item for item in config.models if item.name == name), None)
    if model_config is None:
        raise ValueError(f"模型配置不存在：{name}")
    return model_config


# 根据模型配置动态创建模型实例
def create_chat_model(
    name: str | None = None,
    thinking_enabled: bool = False,
    reasoning_effort: ReasoningEffort | None = None,
    *,
    app_config: AppConfig | None = None,
    model_overrides: dict[str, Any] | None = None,
) -> BaseChatModel:
    config = app_config or get_app_config()
    model_config = _get_model_config(config, name)
    model_class = resolve_model_class(model_config.use)

    model_settings = model_config.model_dump(
        exclude_none=True,
        exclude=_MODEL_METADATA_FIELDS,
    )

    if model_overrides:
        model_settings.update(
            {
                key: value
                for key, value in model_overrides.items()
                if value is not None
            }
        )

    if thinking_enabled:
        if not model_config.supports_thinking:
            raise ValueError(f"模型 {model_config.name} 不支持推理")
        model_settings.update(model_config.when_thinking_enabled or {})
    else:
        model_settings.update(model_config.when_thinking_disabled or {})

    if reasoning_effort is not None:
        if not thinking_enabled:
            raise ValueError("设置推理程度前必须启用推理")
        if not model_config.supports_reasoning_effort:
            raise ValueError(f"模型 {model_config.name} 不支持推理程度")
        model_settings["reasoning_effort"] = reasoning_effort

    return model_class(**model_settings)
