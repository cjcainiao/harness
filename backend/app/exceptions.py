# 全局异常处理

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.schemas.result import Result
from harness.core.logger import get_logger


logger = get_logger(__name__)


# 应用异常
class AppException(Exception):

    def __init__(
        self,
        code: int,
        message: str,
        status_code: int = 400,
        data: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message)


# 构建异常响应
def _build_response(
    status_code: int,
    code: int,
    message: str,
    data: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    result = Result[Any].error(
        code=code,
        message=message,
        data=data,
    )
    return JSONResponse(
        status_code=status_code,
        content=result.model_dump(mode="json"),
        headers=headers,
    )


# 处理应用异常
async def app_exception_handler(
    request: Request,
    error: AppException,
) -> JSONResponse:
    return _build_response(
        status_code=error.status_code,
        code=error.code,
        message=error.message,
        data=error.data,
    )


# 处理HTTP异常
async def http_exception_handler(
    request: Request,
    error: HTTPException,
) -> JSONResponse:
    message = error.detail if isinstance(error.detail, str) else "请求处理失败"
    data = None if isinstance(error.detail, str) else error.detail

    return _build_response(
        status_code=error.status_code,
        code=error.status_code,
        message=message,
        data=data,
        headers=error.headers,
    )


# 处理参数校验异常
async def validation_exception_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    return _build_response(
        status_code=422,
        code=422,
        message="请求参数校验失败",
        data=jsonable_encoder(error.errors()),
    )


# 处理未知异常
async def global_exception_handler(
    request: Request,
    error: Exception,
) -> JSONResponse:
    logger.error(
        "请求处理失败",
        method=request.method,
        path=request.url.path,
        error=str(error),
        exc_info=True,
    )
    return _build_response(
        status_code=500,
        code=500,
        message="服务器内部错误",
    )


# 注册全局异常处理
def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(
        AppException,
        app_exception_handler,
    )
    application.add_exception_handler(
        HTTPException,
        http_exception_handler,
    )
    application.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )
    application.add_exception_handler(
        Exception,
        global_exception_handler,
    )
