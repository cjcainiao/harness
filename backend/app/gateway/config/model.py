# 模型配置接口

import asyncio

from fastapi import APIRouter, Response

from app.exceptions import AppException
from app.schemas.config.model_schema import ModelConfigCreate, ModelConfigInfo, ModelConfigPatch
from app.schemas.result import Result
from app.services.config.model_service import (
    create_model_config,
    delete_model_config,
    list_model_configs,
    set_default_model_config,
    update_model_config,
)


router = APIRouter(prefix="/models", tags=["模型配置"])


# 获取模型配置列表
@router.get("", summary="获取模型配置列表")
async def get_model_configs(response: Response) -> Result[list[ModelConfigInfo]]:
    response.headers["Cache-Control"] = "no-store"
    models = await asyncio.to_thread(list_model_configs)
    return Result.success(models)


# 新增模型配置
@router.post("", summary="新增模型配置")
async def post_model_config(body: ModelConfigCreate, response: Response) -> Result[ModelConfigInfo]:
    response.headers["Cache-Control"] = "no-store"
    try:
        model = await asyncio.to_thread(create_model_config, body.model_dump(exclude_none=True))
    except FileExistsError as error:
        raise AppException(code=409, message="同名模型已存在", status_code=409) from error
    except ValueError as error:
        raise AppException(code=422, message="模型配置无效，无法添加", status_code=422) from error
    return Result.success(model)


# 设置默认模型
@router.patch("/{name:path}/default", summary="设置默认模型")
async def patch_default_model(name: str, response: Response) -> Result[list[ModelConfigInfo]]:
    response.headers["Cache-Control"] = "no-store"
    try:
        models = await asyncio.to_thread(set_default_model_config, name)
    except LookupError as error:
        raise AppException(code=404, message="指定的模型不存在", status_code=404) from error
    except ValueError as error:
        raise AppException(code=422, message="模型配置格式不正确，无法设置默认模型", status_code=422) from error
    return Result.success(models)


# 修改模型配置
@router.patch("/{name:path}", summary="修改模型配置")
async def patch_model_config(
    name: str, body: ModelConfigPatch, response: Response
) -> Result[ModelConfigInfo]:
    response.headers["Cache-Control"] = "no-store"
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise AppException(code=422, message="请填写需要修改的配置", status_code=422)
    try:
        model = await asyncio.to_thread(update_model_config, name, changes)
    except LookupError as error:
        raise AppException(code=404, message="指定的模型不存在", status_code=404) from error
    except ValueError as error:
        raise AppException(code=422, message="模型配置无效，无法保存修改", status_code=422) from error
    return Result.success(model)


# 删除模型配置
@router.delete("/{name:path}", summary="删除模型配置")
async def remove_model_config(name: str, response: Response) -> Result[None]:
    response.headers["Cache-Control"] = "no-store"
    try:
        await asyncio.to_thread(delete_model_config, name)
    except LookupError as error:
        raise AppException(code=404, message="指定的模型不存在", status_code=404) from error
    except ValueError as error:
        raise AppException(code=422, message="模型配置格式不正确，无法删除", status_code=422) from error
    return Result.success(None, "删除成功")
