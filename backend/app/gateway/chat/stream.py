# 模型对话接口

from collections.abc import AsyncIterator

from fastapi import APIRouter, Path
from fastapi.responses import StreamingResponse

from app.exceptions import AppException
from app.schemas.chat.stream_schema import TURN_ID_PATTERN, ChatRequest, StartedTurn
from app.schemas.result import Result
from app.services.chat.stream_service import (
    cancel_chat_turn,
    get_chat_turn,
    prepare_chat_stream,
    start_chat_turn,
    subscribe_chat_turn,
)
from app.services.chat.uploads_service import UploadNotFoundError, UploadStoreError


router = APIRouter(tags=["模型对话"])
# 封装 SSE 响应
def _stream_response(stream: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# 创建后台对话轮次
@router.post("/turns", summary="开始模型对话")
async def create_chat_turn(request: ChatRequest) -> Result[StartedTurn]:
    try:
        started = await start_chat_turn(request)
    except UploadNotFoundError as error:
        raise AppException(code=404, message="附件不存在", status_code=404) from error
    except UploadStoreError as error:
        raise AppException(code=400, message="附件无效，无法开始对话", status_code=400) from error
    except ValueError as error:
        message = str(error)
        if message == "知识库不存在":
            raise AppException(code=404, message=message, status_code=404) from error
        if message in {"轮次标识已用于其他提问", "当前会话仍在回复"}:
            raise AppException(code=409, message=message, status_code=409) from error
        raise AppException(code=422, message="模型配置无效，无法开始对话", status_code=422) from error
    return Result.success(StartedTurn(**started))


# 订阅轮次进度
@router.get("/turns/{turn_id}/events", summary="订阅模型对话进度")
async def chat_turn_events(
    turn_id: str = Path(pattern=TURN_ID_PATTERN),
) -> StreamingResponse:
    try:
        await get_chat_turn(turn_id)
    except LookupError as error:
        raise AppException(code=404, message="轮次不存在", status_code=404) from error
    return _stream_response(subscribe_chat_turn(turn_id))


# 停止后台轮次
@router.post("/turns/{turn_id}/cancel", summary="停止模型对话")
async def stop_chat_turn(
    turn_id: str = Path(pattern=TURN_ID_PATTERN),
) -> Result[StartedTurn]:
    try:
        stopped = await cancel_chat_turn(turn_id)
    except LookupError as error:
        raise AppException(code=404, message="轮次不存在", status_code=404) from error
    return Result.success(StartedTurn(**stopped))


# 模型流式对话
@router.post("/stream", summary="模型流式对话")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    try:
        stream = await prepare_chat_stream(request)
    except UploadNotFoundError as error:
        raise AppException(code=404, message="附件不存在", status_code=404) from error
    except UploadStoreError as error:
        raise AppException(code=400, message="附件无效，无法开始对话", status_code=400) from error
    except ValueError as error:
        if str(error) == "知识库不存在":
            raise AppException(code=404, message="知识库不存在", status_code=404) from error
        raise AppException(code=422, message="模型配置无效，无法开始对话", status_code=422) from error

    return _stream_response(stream)
