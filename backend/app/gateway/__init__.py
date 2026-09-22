# 接口网关

from app.gateway.chat import router as chat_router
from app.gateway.config import router as config_router


__all__ = ["chat_router", "config_router"]
