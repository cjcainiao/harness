# 图片视觉中间件

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, override

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langchain_core.runnables import run_in_executor

from harness.agents.thread_state import ThreadState
from harness.config.app_config import get_app_config


# 本次工具调用成功查看的图片路径
def _current_image_paths(messages: list[AnyMessage]) -> list[str]:
    last_index = next(
        (index for index in range(len(messages) - 1, -1, -1) if not isinstance(messages[index], ToolMessage)),
        None,
    )
    if last_index is None or not isinstance(messages[last_index], AIMessage):
        return []

    calls = messages[last_index].tool_calls
    if not calls or not all(call.get("id") for call in calls):
        return []

    # 等待同一批工具全部返回
    results: dict[str, ToolMessage] = {}
    for message in messages[last_index + 1 :]:
        if not isinstance(message, ToolMessage):
            return []
        results[message.tool_call_id] = message
    if not all(call["id"] in results for call in calls):
        return []

    # 只取本次成功的图片查看结果
    paths: list[str] = []
    for call in calls:
        if call.get("name") != "view_image":
            continue
        result = results[call["id"]]
        if result.status == "error" or not isinstance(result.content, str):
            continue
        try:
            payload = json.loads(result.content)
        except json.JSONDecodeError:
            continue
        image_path = payload.get("image_path") if isinstance(payload, dict) else None
        arguments = call.get("args")
        called_path = arguments.get("image_path") if isinstance(arguments, dict) else None
        if isinstance(image_path, str) and isinstance(called_path, str) and Path(image_path) == Path(called_path):
            if image_path not in paths:
                paths.append(image_path)
    return paths


# 重新读取工具校验过的图片
def _image_data_url(image_path: str, image_data: Any, workspace: Path, max_bytes: int) -> str | None:
    if not isinstance(image_data, dict):
        return None
    path = Path(image_path)
    actual_path = image_data.get("actual_path")
    mime_type = image_data.get("mime_type")
    size = image_data.get("size")
    digest = image_data.get("sha256")
    expected_path = workspace / "uploads" / path.parent.name / "content"
    if (
        not path.is_absolute()
        or path != expected_path
        or not isinstance(actual_path, str)
        or Path(actual_path) != expected_path
        or mime_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}
        or type(size) is not int
        or size < 1
        or size > max_bytes
        or not isinstance(digest, str)
    ):
        return None
    if any(item.is_symlink() for item in (workspace, workspace / "uploads", path.parent, path)):
        return None

    try:
        with path.open("rb") as stream:
            content = stream.read(max_bytes + 1)
    except OSError:
        return None
    if len(content) != size or hashlib.sha256(content).hexdigest() != digest:
        return None
    return f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}"


# 图片视觉消息处理
class ViewImageMiddleware(AgentMiddleware[ThreadState]):
    state_schema = ThreadState

    # 只在模型请求中注入本次查看的图片
    def _inject(self, request: ModelRequest) -> ModelRequest:
        paths = _current_image_paths(request.messages)
        if not paths:
            return request

        model_name = getattr(request.model, "model_name", None)
        config = get_app_config()
        model_config = next((item for item in config.models if item.model_name == model_name), None)
        if model_config is None or not model_config.supports_vision:
            message = HumanMessage(content="当前模型不支持视觉，无法查看图片，请告知用户切换支持视觉的模型。")
            return request.override(messages=[*request.messages, message])

        state = request.state or {}
        viewed_images = state.get("viewed_images") or {}
        workspace_path = state.get("workspace_path")
        if not isinstance(workspace_path, str) or not isinstance(viewed_images, dict):
            return request

        # 图片内容只存在于本次模型请求
        workspace = Path(workspace_path)
        content: list[dict[str, Any]] = [{"type": "text", "text": "本次查看的图片："}]
        for image_path in paths:
            data_url = _image_data_url(
                image_path,
                viewed_images.get(image_path),
                workspace,
                config.system.upload_max_bytes,
            )
            if data_url is None:
                content.append({"type": "text", "text": f"图片已更改或无法读取：{image_path}。请不要根据它的内容作答。"})
                continue
            content.extend(
                [
                    {"type": "text", "text": image_path},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            )

        message = HumanMessage(content=content, additional_kwargs={"hide_from_ui": True})
        return request.override(messages=[*request.messages, message])

    # 包装同步模型调用
    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        return handler(self._inject(request))

    # 包装异步模型调用
    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        injected = await run_in_executor(None, self._inject, request)
        return await handler(injected)
