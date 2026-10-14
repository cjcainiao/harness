# 对话模型接口

import asyncio

from fastapi import APIRouter

from app.schemas.chat.model_schema import ModelInfo
from app.schemas.result import Result
from app.services.chat.model_service import list_chat_models


router = APIRouter(prefix="/models", tags=["对话模型"])


# 获取对话可选模型
@router.get("", summary="获取对话可选模型")
async def get_chat_models() -> Result[list[ModelInfo]]:
    models = await asyncio.to_thread(list_chat_models)
    return Result.success(models)
