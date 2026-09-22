# 系统配置接口

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.result import Result
from harness.config.app_config import AppConfig, get_app_config
from harness.config.model_config import ModelConfig
from harness.utils.yaml_util import dump_yaml, load_yaml_keep_comment


router = APIRouter(prefix="/config", tags=["系统配置"])


# 模型信息（不暴露密钥）
class ModelInfo(BaseModel):
    name: str = Field(description="模型名称")
    display_name: str = Field(description="模型显示名称")
    description: str | None = Field(default=None, description="模型描述")
    use: str = Field(description="模型实现类")
    model: str = Field(description="服务商模型名称")
    supports_thinking: bool = Field(default=False, description="是否支持推理")
    supports_reasoning_effort: bool = Field(default=False, description="是否支持推理程度")
    supports_vision: bool = Field(default=False, description="是否支持视觉")
    context_window: int | None = Field(default=None, description="模型上下文长度")


# 获取模型列表
@router.get("/models", summary="获取模型列表")
async def get_models() -> Result[list[ModelInfo]]:
    config = get_app_config()

    models = [
        ModelInfo(
            name=model.name,
            display_name=model.display_name or model.name,
            description=model.description,
            use=model.use,
            model=model.model,
            supports_thinking=model.supports_thinking,
            supports_reasoning_effort=model.supports_reasoning_effort,
            supports_vision=model.supports_vision,
            context_window=model.context_window,
        )
        for model in config.models
    ]
    return Result.success(models)

# 修改模型配置
@router.put("/models/{name}", summary="修改模型配置", response_model=Result)
async def update_model(model: ModelConfig):
    config_path = AppConfig.resolve_config_path()
    data = load_yaml_keep_comment(config_path)
    models = data.get("models") or []
    target = next((m for m in models if m.get("name") == model.name), None)
    if target is None:
        return Result.error(code=404, message=f"模型不存在：{model.name}")

    # 合并本次传入的字段，未传的保留原值
    target.update(model.model_dump(exclude_none=True, exclude_unset=True))
    dump_yaml(config_path, data)
    return Result.success(None, "修改成功")

# 新增模型配置
@router.post("/models", summary="新增模型配置", response_model=Result)
async def create_model(model: ModelConfig):
    config_path = AppConfig.resolve_config_path()
    data = load_yaml_keep_comment(config_path)
    models = data.get("models") or []
    exists = any(m.get("name") == model.name for m in models)
    if exists:
        return Result.error(code=409, message=f"模型已存在：{model.name}")

    models.append(model.model_dump(exclude_none=True))
    data["models"] = models
    dump_yaml(config_path, data)
    return Result.success(None, "新增成功")


# 删除模型配置
@router.delete("/models", summary="删除模型配置", response_model=Result)
async def delete_model(name: str):
    config_path = AppConfig.resolve_config_path()
    data = load_yaml_keep_comment(config_path)
    models = data.get("models") or []
    remaining = [m for m in models if m.get("name") != name]
    if len(remaining) == len(models):
        return Result.error(code=404, message=f"模型不存在：{name}")

    data["models"] = remaining
    dump_yaml(config_path, data)
    return Result.success(None, "删除成功")

