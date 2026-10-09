# 接口网关

from app.gateway.chat import router as chat_router
from app.gateway.config import router as config_router
from app.gateway.history import router as history_router
from app.gateway.uploads import router as uploads_router


__all__ = ["chat_router", "config_router", "history_router", "uploads_router"]
