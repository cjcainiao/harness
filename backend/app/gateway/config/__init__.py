# 配置接口模块

from fastapi import APIRouter

from app.gateway.config.mcp import router as mcp_router
from app.gateway.config.model import router as model_router
from app.gateway.config.skill import router as skill_router


router = APIRouter(prefix="/config")
router.include_router(model_router)
router.include_router(mcp_router)
router.include_router(skill_router)


__all__ = ["router"]
