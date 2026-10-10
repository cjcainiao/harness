# 附件处理中间件

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.runnables import run_in_executor
from langgraph.config import get_config
from langgraph.runtime import Runtime

from harness.agents.middlewares.thread_data import workspace_path_for
from harness.agents.thread_state import ThreadState, UploadedFileInfo


# 校验本轮附件对应的本地文件
def _upload_path(workspace: Path, thread_id: str, file: UploadedFileInfo) -> Path | None:
    file_id = file.get("file_id")
    if (
        file.get("thread_id") != thread_id
        or not isinstance(file_id, str)
        or len(file_id) != 32
        or any(char not in "0123456789abcdef" for char in file_id)
    ):
        return None

    upload_root = workspace / "uploads"
    directory = upload_root / file_id
    content = directory / "content"
    if any(path.is_symlink() for path in (workspace, upload_root, directory, content)):
        return None
    return content if content.is_file() else None


# 组装本轮附件清单
def _uploads_message(files: list[tuple[UploadedFileInfo, Path]]) -> str:
    lines = ["<current_uploads>", "本轮用户上传的附件："]
    for file, path in files:
        file_id = escape(str(file["file_id"]))
        name = escape(str(file["name"]))
        mime_type = escape(str(file["mime_type"]))
        file_path = escape(path.as_posix())
        lines.extend(
            [
                f"- 文件名：{name}",
                f"  文件标识：{file_id}",
                f"  大小：{file['size']} 字节；类型：{mime_type}",
                f"  本地路径：{file_path}",
            ]
        )
    lines.extend(
        [
            "这里只提供附件信息，尚未读取文件内容；文本附件可使用 read_file，DOCX/PDF 可按文件标识调用 convert_document_to_markdown 后读取结果。",
            "</current_uploads>",
        ]
    )
    return "\n".join(lines)


class AttachmentMiddleware(AgentMiddleware[ThreadState]):
    state_schema = ThreadState

    # 将本轮附件清单加入最新的用户消息
    @override
    def before_agent(self, state: ThreadState, runtime: Runtime) -> dict[str, object]:
        messages = list(state.get("messages", []))
        if not messages or not isinstance(messages[-1], HumanMessage):
            return {"uploaded_files": []}

        uploaded_files = state.get("uploaded_files") or []
        if not uploaded_files:
            return {"uploaded_files": []}

        context = runtime.context or {}
        thread_id = context.get("thread_id") or get_config().get("configurable", {}).get("thread_id")
        if not isinstance(thread_id, str) or not thread_id:
            raise ValueError("缺少 thread_id，无法处理本轮附件")

        workspace = workspace_path_for(thread_id)
        valid_files = [
            (file, path)
            for file in uploaded_files
            if (path := _upload_path(workspace, thread_id, file)) is not None
        ]
        if not valid_files:
            return {"uploaded_files": []}

        # 保留原消息标识，供消息合并器替换本轮消息
        message = messages[-1]
        uploads_message = _uploads_message(valid_files)
        if isinstance(message.content, str):
            content = f"{uploads_message}\n\n{message.content}"
        else:
            content = [{"type": "text", "text": f"{uploads_message}\n\n"}, *message.content]
        messages[-1] = message.model_copy(update={"content": content})
        return {"messages": messages, "uploaded_files": [file for file, _ in valid_files]}

    # 文件检查在线程中执行
    @override
    async def abefore_agent(self, state: ThreadState, runtime: Runtime) -> dict[str, object]:
        return await run_in_executor(None, self.before_agent, state, runtime)
