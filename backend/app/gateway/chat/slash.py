# 斜杠菜单接口

from fastapi import APIRouter, HTTPException, Query

from app.schemas.chat.slash import SlashCommandItem
from app.schemas.result import Result
from app.services.chat.slash import list_slash_menu


router = APIRouter(prefix="/slash", tags=["斜杠菜单"])


# 查询斜杠菜单
@router.get("", summary="获取斜杠菜单")
async def get_slash_menu(
    command: str | None = Query(default=None, description="一级命令名称，未提供时查询一级命令"),
    query: str | None = Query(default=None, description="当前菜单的名称关键词"),
) -> Result[list[SlashCommandItem]]:
    items = await list_slash_menu(command, query)
    if items is None:
        raise HTTPException(status_code=404, detail="命令不存在或未启用")
    return Result.success(items)
