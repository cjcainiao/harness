# 模型对话业务

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from collections.abc import AsyncIterator
from contextlib import aclosing
from dataclasses import dataclass, field
from typing import Any

from app.schemas.chat.stream_schema import ChatAttachment, ChatRequest
from app.services.chat.uploads_service import get_upload, uploaded_file_info
from harness.agents.thread_state import UploadedFileInfo
from harness.core.logger import get_logger
from harness.models.factory import validate_model_options
from harness.rag.retrieval.repository import base_exists
from harness.runtime.stream import stream_agent
from harness.storage import history
from harness.storage.recorder import TurnRecorder


logger = get_logger(__name__)


# 正在运行的轮次
@dataclass
class ChatJob:
    turn_id: str
    thread_id: str
    task: asyncio.Task[None] | None = None
    recorder: TurnRecorder = field(default_factory=TurnRecorder)
    subscribers: set[asyncio.Queue[dict[str, Any]]] = field(default_factory=set)
    status: str = history.TURN_STREAMING
    questions: list[str] = field(default_factory=list)
    finished: bool = False

    # 广播事件并更新快照
    def publish(self, event: dict[str, Any]) -> None:
        self.recorder.feed(event)
        if event.get("type") == "answer_complete":
            self.status = history.TURN_COMPLETED
        elif event.get("type") == "error":
            self.status = history.TURN_FAILED
        elif event.get("type") == "follow_up_questions":
            self.questions = event.get("questions", [])
        elif event.get("type") == "done":
            self.finished = True
        for subscriber in tuple(self.subscribers):
            subscriber.put_nowait(event)


_jobs: dict[str, ChatJob] = {}
_start_lock = asyncio.Lock()


# 校验并加载本轮附件
def _uploaded_file_infos(
    thread_id: str, attachments: list[ChatAttachment]
) -> list[UploadedFileInfo]:
    return [uploaded_file_info(get_upload(thread_id, item.file_id)) for item in attachments]


# 校验模型、知识库和附件
async def _validated_files(request: ChatRequest) -> list[UploadedFileInfo]:
    validate_model_options(request.model_name, request.thinking_enabled, request.reasoning_effort)
    if request.knowledge_base_id is not None and not await asyncio.to_thread(
        base_exists, request.knowledge_base_id
    ):
        raise ValueError("知识库不存在")
    if request.thread_id is not None and request.attachments:
        return await asyncio.to_thread(_uploaded_file_infos, request.thread_id, request.attachments)
    return []


# 原流式入口
async def prepare_chat_stream(request: ChatRequest) -> AsyncIterator[str]:
    uploaded_files = await _validated_files(request)
    return stream_agent(
        message=request.message,
        thread_id=request.thread_id,
        uploaded_files=uploaded_files,
        model_name=request.model_name,
        thinking_enabled=request.thinking_enabled,
        reasoning_effort=request.reasoning_effort,
        knowledge_base_id=request.knowledge_base_id,
    )


# 执行独立轮次
async def _run_job(
    job: ChatJob, request: ChatRequest, uploaded_files: list[UploadedFileInfo]
) -> None:
    try:
        stream = stream_agent(
            message=request.message,
            thread_id=job.thread_id,
            turn_id=job.turn_id,
            uploaded_files=uploaded_files,
            model_name=request.model_name,
            thinking_enabled=request.thinking_enabled,
            reasoning_effort=request.reasoning_effort,
            knowledge_base_id=request.knowledge_base_id,
        )
        async with aclosing(stream):
            async for chunk in stream:
                if not chunk.startswith("data: "):
                    continue
                event = json.loads(chunk[6:].strip())
                if isinstance(event, dict):
                    job.publish(event)
    except asyncio.CancelledError:
        if job.status != history.TURN_COMPLETED:
            job.status = history.TURN_INTERRUPTED
        raise
    except Exception as error:
        logger.error("后台对话执行失败", turn_id=job.turn_id, error=str(error), exc_info=True)
        job.publish({"type": "error", "code": 500, "message": "服务器内部错误"})
    finally:
        if job.status == history.TURN_STREAMING:
            job.status = history.TURN_INTERRUPTED
        if job.status == history.TURN_INTERRUPTED:
            job.publish({"type": "interrupted"})
        try:
            await asyncio.to_thread(
                history.update_turn,
                job.turn_id,
                job.status,
                job.recorder.segments(),
                job.recorder.usage(),
            )
            if job.questions:
                await asyncio.to_thread(
                    history.save_follow_up_questions, job.turn_id, job.questions
                )
        except sqlite3.Error as error:
            logger.warning("后台对话历史写入失败", turn_id=job.turn_id, error=str(error))
        if not job.finished:
            job.publish({"type": "done", "thread_id": job.thread_id})
        job.finished = True
        _jobs.pop(job.turn_id, None)


# 创建独立轮次
async def start_chat_turn(request: ChatRequest) -> dict[str, str]:
    turn_id = request.turn_id or uuid.uuid4().hex
    async with _start_lock:
        existing = await history.get_turn(turn_id)
        thread_id = request.thread_id or (existing["thread_id"] if existing else uuid.uuid4().hex)
        if existing is not None:
            if (
                existing["thread_id"] != thread_id
                or existing["question"]["content"] != request.message
            ):
                raise ValueError("轮次标识已用于其他提问")
            return {"thread_id": thread_id, "turn_id": turn_id, "status": existing["status"]}
        if any(job.thread_id == thread_id for job in _jobs.values()):
            raise ValueError("当前会话仍在回复")
        uploaded_files = await _validated_files(request)
        await asyncio.to_thread(
            history.start_turn,
            thread_id,
            request.message,
            uploaded_files,
            turn_id=turn_id,
        )
        job = ChatJob(turn_id=turn_id, thread_id=thread_id)
        _jobs[turn_id] = job
        job.task = asyncio.create_task(_run_job(job, request, uploaded_files))
    return {"thread_id": thread_id, "turn_id": turn_id, "status": history.TURN_STREAMING}


# 编码流式事件
def _sse(event: dict[str, Any]) -> str:
    data = json.dumps(event, ensure_ascii=False, default=str, separators=(",", ":"))
    return f"data: {data}\n\n"


# 订阅轮次进度
async def subscribe_chat_turn(turn_id: str) -> AsyncIterator[str]:
    job = _jobs.get(turn_id)
    if job is None or job.finished:
        turn = await history.get_turn(turn_id)
        if turn is None:
            raise LookupError("轮次不存在")
        yield _sse(
            {
                "type": "turn_snapshot",
                "items": turn["items"],
                "usage": turn["usage"],
                "status": turn["status"],
                "questions": turn["follow_up_questions"],
            }
        )
        if turn["status"] == history.TURN_STREAMING:
            yield _sse({"type": "interrupted"})
        yield _sse({"type": "done", "thread_id": turn["thread_id"]})
        return
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    job.subscribers.add(queue)
    try:
        yield _sse(
            {
                "type": "turn_snapshot",
                "items": job.recorder.segments(),
                "usage": job.recorder.usage(),
                "status": job.status,
                "questions": job.questions,
            }
        )
        while True:
            event = await queue.get()
            yield _sse(event)
            if event.get("type") == "done":
                return
    finally:
        job.subscribers.discard(queue)


# 读取单轮历史
async def get_chat_turn(turn_id: str) -> dict[str, Any]:
    turn = await history.get_turn(turn_id)
    if turn is None:
        raise LookupError("轮次不存在")
    return turn


# 取消运行中的轮次
async def cancel_chat_turn(turn_id: str) -> dict[str, str]:
    turn = await get_chat_turn(turn_id)
    job = _jobs.get(turn_id)
    if job and job.task and not job.task.done():
        job.task.cancel()
        try:
            await job.task
        except asyncio.CancelledError:
            pass
        turn = await get_chat_turn(turn_id)
    elif turn["status"] == history.TURN_STREAMING:
        await asyncio.to_thread(
            history.update_turn,
            turn_id,
            history.TURN_INTERRUPTED,
            turn["items"],
            turn["usage"],
        )
        turn["status"] = history.TURN_INTERRUPTED
    return {"thread_id": turn["thread_id"], "turn_id": turn_id, "status": turn["status"]}


# 取消会话内的任务
async def cancel_thread_tasks(thread_id: str) -> None:
    for job in tuple(_jobs.values()):
        if job.thread_id == thread_id:
            await cancel_chat_turn(job.turn_id)


# 关闭全部对话任务
async def shutdown_chat_tasks() -> None:
    for job in tuple(_jobs.values()):
        await cancel_chat_turn(job.turn_id)
