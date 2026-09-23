# 模型工厂

import importlib
from typing import Any

from langchain.chat_models import BaseChatModel

from harness.config.app_config import AppConfig, get_app_config
from harness.config.model_config import ModelConfig

# 档位值由模型配置校验
type ReasoningEffort = str

# 不传入模型构造函数的配置字段
_MODEL_METADATA_FIELDS = {
    "name",
    "display_name",
    "description",
    "use",
    "supports_thinking",
    "reasoning_levels",
    "when_thinking_enabled",
    "when_thinking_disabled",
    "supports_vision",
    "context_window",
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


# 校验模型与推理参数
def validate_model_options(
    name: str | None,
    thinking_enabled: bool,
    reasoning_effort: ReasoningEffort | None,
    *,
    app_config: AppConfig | None = None,
) -> ModelConfig:
    config = app_config or get_app_config()
    model_config = _get_model_config(config, name)

    if thinking_enabled and not model_config.supports_thinking:
        raise ValueError(f"模型 {model_config.name} 不支持推理")
    if reasoning_effort is not None:
        if not thinking_enabled:
            raise ValueError("设置推理程度前必须启用推理")
        if reasoning_effort not in model_config.reasoning_levels:
            supported = "、".join(model_config.reasoning_levels) or "无"
            raise ValueError(f"模型 {model_config.name} 不支持推理强度 {reasoning_effort}，可选：{supported}")

        model_class = resolve_model_class(model_config.use)
        if not callable(getattr(model_class, "reasoning_model_kwargs", None)):
            raise ValueError(f"模型 {model_config.name} 的适配类未实现推理强度参数映射")

    return model_config


# 递归合并嵌套模型参数
def _merge_model_settings(settings: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(settings.get(key), dict):
            nested = dict(settings[key])
            _merge_model_settings(nested, value)
            settings[key] = nested
        else:
            settings[key] = value


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
    model_config = validate_model_options(name, thinking_enabled, reasoning_effort, app_config=config)
    model_class = resolve_model_class(model_config.use)

    model_settings = model_config.model_dump(
        exclude_none=True,
        exclude=_MODEL_METADATA_FIELDS,
    )

    if model_overrides:
        _merge_model_settings(
            model_settings,
            {key: value for key, value in model_overrides.items() if value is not None},
        )

    if thinking_enabled:
        _merge_model_settings(model_settings, model_config.when_thinking_enabled or {})
    else:
        _merge_model_settings(model_settings, model_config.when_thinking_disabled or {})

    if reasoning_effort is not None:
        reasoning_kwargs = model_class.reasoning_model_kwargs(reasoning_effort)
        _merge_model_settings(model_settings, reasoning_kwargs)

    return model_class(**model_settings)
