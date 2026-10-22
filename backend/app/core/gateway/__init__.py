# 接口网关

from app.core.gateway.chat import router as chat_router
from app.core.gateway.config import router as config_router
from app.core.gateway.knowledge import router as knowledge_router


__all__ = [
    "chat_router",
    "config_router",
    "knowledge_router",
]
