# 全局启动文件

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.exceptions import register_exception_handlers
from app.gateway import chat_router, config_router
from harness.config.app_config import get_app_config
from harness.core.logger import get_logger, shutdown_logging


logger = get_logger(__name__)


# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_app_config()
    logger.info("应用启动中", app_name=config.system.app_name, env=config.system.env)
    try:
        yield
    finally:
        logger.info("应用关闭中", app_name=config.system.app_name)
        shutdown_logging()


async def health_check() -> dict[str, str]:
    logger.info("执行健康检查")
    return {"status": "ok"}


# 创建应用
def create_app() -> FastAPI:
    config = get_app_config()
    application = FastAPI(
        title=config.system.app_name,
        debug=config.system.debug,
        lifespan=lifespan,
    )

    # 注册全局异常处理
    register_exception_handlers(application)

    # 路由前缀
    api_prefix = config.system.api_prefix
    # 注册接口路由
    application.include_router(chat_router, prefix=api_prefix)
    application.include_router(config_router, prefix=api_prefix)

    # CORS 配置，解决跨域问题
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.system.allow_origins,
        allow_credentials=config.system.allow_credentials,
        allow_methods=config.system.allow_methods,
        allow_headers=config.system.allow_headers,
    )
    application.add_api_route("/health", health_check, methods=["GET"], summary="健康检测接口")
    return application


# 全局应用实例
app = create_app()


if __name__ == "__main__":
    config = get_app_config()
    uvicorn.run(
        "app.main:app",
        host=config.system.host,
        port=config.system.port,
        log_config=None,
        reload=False,
    )
