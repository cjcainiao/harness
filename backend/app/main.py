# 全局启动文件

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.exceptions import register_exception_handlers
from app.gateway import chat_router, config_router, history_router
from harness.config.app_config import get_app_config
from harness.core.logger import get_logger, shutdown_logging
from harness.runtime.checkpointer import init_checkpointer, shutdown_checkpointer
from harness.runtime.db_path import resolve_db_path
from harness.storage.db import init_history_db


logger = get_logger(__name__)


# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_app_config()
    logger.info("应用启动中", app_name=config.system.app_name, env=config.system.env)
    try:
        # 表结构已是最新时只做一次存在性检查
        db_path = await init_history_db()
        logger.info("历史库已就绪", path=str(db_path))

        # 检查点写磁盘文件，进程重启后同一会话仍能延续
        checkpointer = await init_checkpointer()
        if checkpointer is None:
            logger.info("检查点记忆已关闭")
        else:
            logger.info(
                "检查点库已就绪",
                path=str(resolve_db_path(config.memory.db_path)),
                durability=config.memory.durability,
            )
        yield
    finally:
        logger.info("应用关闭中", app_name=config.system.app_name)
        await shutdown_checkpointer()
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
    application.include_router(history_router, prefix=api_prefix)

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
