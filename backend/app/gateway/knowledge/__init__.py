# 知识库接口路由

from fastapi import APIRouter

from app.gateway.knowledge.document import router as document_router


router = APIRouter(prefix="/knowledge")
router.include_router(document_router)


__all__ = ["router"]
