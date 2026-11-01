# 对话接口路由

from fastapi import APIRouter

from app.core.gateway.chat.generated_images import router as generated_images_router
from app.core.gateway.chat.history import router as history_router
from app.core.gateway.chat.model import router as model_router
from app.core.gateway.chat.search import router as search_router
from app.core.gateway.chat.slash import router as slash_router
from app.core.gateway.chat.stream import router as stream_router
from app.core.gateway.chat.uploads import router as uploads_router


router = APIRouter(prefix="/chat")
router.include_router(stream_router)
router.include_router(history_router)
router.include_router(model_router)
router.include_router(slash_router)
router.include_router(search_router)
router.include_router(uploads_router)
router.include_router(generated_images_router)


__all__ = ["router"]
