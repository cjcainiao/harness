# 模型配置业务

from app.schemas.config.model import ModelInfo
from harness.config.app_config import AppConfig, get_app_config
from harness.config.model_config import ModelConfig
from harness.utils.yaml_util import dump_yaml, load_yaml_keep_comment


# 模型配置错误
class ModelConfigManagementError(ValueError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


# 获取模型列表
def list_model_configs() -> list[ModelInfo]:
    return [
        ModelInfo(
            model_name=model.model_name,
            display_name=model.display_name or model.model_name,
            description=model.description,
            provider=model.provider,
            use=model.use,
            supports_thinking=model.supports_thinking,
            reasoning_levels=model.reasoning_levels,
            supports_vision=model.supports_vision,
            context_window=model.context_window,
        )
        for model in get_app_config().models
    ]


# 修改模型配置
def update_model_config(model_name: str, model: ModelConfig) -> None:
    config_path = AppConfig.resolve_config_path()
    data = load_yaml_keep_comment(config_path)
    models = data.get("models") or []
    target = next((item for item in models if item.get("model_name") == model_name), None)
    if target is None:
        raise ModelConfigManagementError(404, f"模型不存在：{model_name}")
    if model.model_name != model_name and any(
        item.get("model_name") == model.model_name for item in models
    ):
        raise ModelConfigManagementError(409, f"模型已存在：{model.model_name}")

    # 合并本次传入的字段
    target.update(model.model_dump(exclude_none=True, exclude_unset=True))
    dump_yaml(config_path, data)


# 新增模型配置
def create_model_config(model: ModelConfig) -> None:
    config_path = AppConfig.resolve_config_path()
    data = load_yaml_keep_comment(config_path)
    models = data.get("models") or []
    if any(item.get("model_name") == model.model_name for item in models):
        raise ModelConfigManagementError(409, f"模型已存在：{model.model_name}")

    models.append(model.model_dump(exclude_none=True))
    data["models"] = models
    dump_yaml(config_path, data)


# 删除模型配置
def delete_model_config(model_name: str) -> None:
    config_path = AppConfig.resolve_config_path()
    data = load_yaml_keep_comment(config_path)
    models = data.get("models") or []
    remaining = [item for item in models if item.get("model_name") != model_name]
    if len(remaining) == len(models):
        raise ModelConfigManagementError(404, f"模型不存在：{model_name}")

    data["models"] = remaining
    dump_yaml(config_path, data)
