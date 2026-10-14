# 技能包配置接口

import asyncio
from typing import Annotated

from fastapi import APIRouter, File, Response, UploadFile

from app.exceptions import AppException
from app.schemas.config.skill_schema import SkillConfigInfo, SkillEnabledPatch
from app.schemas.result import Result
from app.services.config.skill_service import (
    SkillUploadNameError,
    SkillUploadTooLargeError,
    delete_skill_config,
    install_skill_config,
    list_skill_configs,
    set_skill_config_enabled,
)


router = APIRouter(prefix="/skills", tags=["技能包配置"])


# 安装第三方技能包
@router.post("", summary="安装第三方技能包")
async def post_skill(
    file: Annotated[UploadFile, File()], response: Response
) -> Result[SkillConfigInfo]:
    response.headers["Cache-Control"] = "no-store"
    try:
        skill = await asyncio.to_thread(install_skill_config, file.filename, file.file)
    except SkillUploadTooLargeError as error:
        raise AppException(code=413, message="技能压缩包超过大小限制", status_code=413) from error
    except SkillUploadNameError as error:
        raise AppException(
            code=422,
            message="SKILL.md 的 name 必须以小写字母或数字开头，且只能包含小写字母、数字和连字符",
            status_code=422,
        ) from error
    except FileExistsError as error:
        raise AppException(code=409, message="同名技能包已存在", status_code=409) from error
    except ValueError as error:
        raise AppException(code=422, message="技能压缩包无效，无法安装", status_code=422) from error
    finally:
        await file.close()
    return Result.success(skill)


# 获取技能包列表
@router.get("", summary="获取技能包列表")
async def get_skill_configs(response: Response) -> Result[list[SkillConfigInfo]]:
    response.headers["Cache-Control"] = "no-store"
    skills = await asyncio.to_thread(list_skill_configs)
    return Result.success(skills)


# 修改第三方技能启停状态
@router.patch("/{name}/enabled", summary="启用或停用第三方技能")
async def patch_skill_enabled(
    name: str, body: SkillEnabledPatch, response: Response
) -> Result[SkillConfigInfo]:
    response.headers["Cache-Control"] = "no-store"
    try:
        skill = await asyncio.to_thread(set_skill_config_enabled, name, body.enabled)
    except FileNotFoundError as error:
        raise AppException(code=404, message="指定的第三方技能不存在", status_code=404) from error
    except FileExistsError as error:
        raise AppException(code=409, message="技能目录存在同名冲突", status_code=409) from error
    except ValueError as error:
        raise AppException(code=422, message="技能包无效，无法切换启用状态", status_code=422) from error
    return Result.success(skill)


# 删除第三方技能包
@router.delete("/{name}", summary="删除第三方技能包")
async def delete_skill(name: str, response: Response) -> Result[None]:
    response.headers["Cache-Control"] = "no-store"
    try:
        await asyncio.to_thread(delete_skill_config, name)
    except FileNotFoundError as error:
        raise AppException(code=404, message="指定的第三方技能不存在", status_code=404) from error
    except FileExistsError as error:
        raise AppException(code=409, message="技能目录存在同名冲突", status_code=409) from error
    except ValueError as error:
        raise AppException(code=422, message="技能包无效，无法删除", status_code=422) from error
    return Result.success(None, "删除成功")
