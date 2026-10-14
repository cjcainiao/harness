# 模型对话接口

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.exceptions import AppException
from app.schemas.chat.stream_schema import ChatRequest
from app.services.chat.stream_service import prepare_chat_stream
from app.services.chat.uploads_service import UploadNotFoundError, UploadStoreError


router = APIRouter(tags=["模型对话"])


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
        raise AppException(code=422, message="模型配置无效，无法开始对话", status_code=422) from error

    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
