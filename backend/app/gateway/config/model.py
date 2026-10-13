# 模型配置接口

import asyncio

from fastapi import APIRouter

from app.schemas.config.model import ModelInfo
from app.schemas.result import Result
from app.services.config.model import (
    ModelConfigManagementError,
    create_model_config,
    delete_model_config,
    list_model_configs,
    update_model_config,
)
from harness.config.model_config import ModelConfig


router = APIRouter(prefix="/models", tags=["模型配置"])


# 获取模型列表
@router.get("", summary="获取模型列表")
async def get_models() -> Result[list[ModelInfo]]:
    models = await asyncio.to_thread(list_model_configs)
    return Result.success(models)


# 修改模型配置
@router.put("/{model_name}", summary="修改模型配置")
async def update_model(model_name: str, model: ModelConfig) -> Result[None]:
    try:
        await asyncio.to_thread(update_model_config, model_name, model)
    except ModelConfigManagementError as error:
        return Result.error(code=error.status_code, message=str(error))
    return Result.success(None, "修改成功")


# 新增模型配置
@router.post("", summary="新增模型配置")
async def create_model(model: ModelConfig) -> Result[None]:
    try:
        await asyncio.to_thread(create_model_config, model)
    except ModelConfigManagementError as error:
        return Result.error(code=error.status_code, message=str(error))
    return Result.success(None, "新增成功")


# 删除模型配置
@router.delete("", summary="删除模型配置")
async def delete_model(model_name: str) -> Result[None]:
    try:
        await asyncio.to_thread(delete_model_config, model_name)
    except ModelConfigManagementError as error:
        return Result.error(code=error.status_code, message=str(error))
    return Result.success(None, "删除成功")
