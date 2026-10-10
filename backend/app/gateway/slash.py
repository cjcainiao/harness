# 斜杠菜单接口

from fastapi import APIRouter, Query

from app.schemas.result import Result


router = APIRouter(prefix="/slash", tags=["斜杠菜单"])


# 按命令获取菜单内容
@router.get("", summary="获取斜杠菜单")
async def get_slash_menu(
    command: str | None = Query(default=None, description="命令名称，未提供时返回一级命令"),
) -> Result[dict[str, object]]:
    raise NotImplementedError("斜杠菜单查询尚未实现")
