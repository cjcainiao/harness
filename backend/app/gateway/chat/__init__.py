# 对话接口路由

from fastapi import APIRouter

from app.gateway.chat.history import router as history_router
from app.gateway.chat.slash import router as slash_router
from app.gateway.chat.stream import router as stream_router
from app.gateway.chat.uploads import router as uploads_router


router = APIRouter(prefix="/chat")
router.include_router(stream_router)
router.include_router(history_router)
router.include_router(slash_router)
router.include_router(uploads_router)


__all__ = ["router"]
