# 全局启动文件

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from harness.config.app_config import get_app_config
from harness.core.logger import configure_logging, get_logger, shutdown_logging

system = get_app_config().system

# 初始化日志系统
configure_logging(
    level=system.log_level,
    env=system.env,
    log_dir=system.log_dir,
    max_bytes=system.log_max_bytes,
    backup_count=system.log_backup_count,
    console=system.log_console,
)
logger = get_logger(__name__)


# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("应用启动中", app_name=system.app_name, env=system.env)
    try:
        yield
    finally:
        logger.info("应用关闭中", app_name=system.app_name)
        shutdown_logging()


app = FastAPI(
    title=system.app_name,
    debug=system.debug,
    lifespan=lifespan,
)

# CORS 配置，解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", summary="健康检测接口")
async def health_check() -> dict[str, str]:
    logger.info("执行健康检查")
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=system.host,
        port=system.port,
        log_config=None,
        reload=False,
    )
