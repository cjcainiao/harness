# 显式技能激活中间件

from __future__ import annotations

from collections.abc import Awaitable, Callable
from html import escape
from pathlib import Path
from typing import override

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage

from harness.skills.loader import load_skills


# 提取用户消息中的文字
def _message_text(message: HumanMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    parts: list[str] = []
    for item in message.content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "\n".join(parts)


# 跳过服务端添加的本轮附件说明
def _original_user_text(message: HumanMessage, uploaded_files: object) -> str:
    text = _message_text(message)
    if isinstance(uploaded_files, list) and uploaded_files and text.startswith("<current_uploads>"):
        _, marker, remaining = text.partition("</current_uploads>")
        if marker:
            return remaining.lstrip("\r\n")
    return text


# 解析开头的技能命令
def _skill_name(text: str) -> str | None:
    if not text.startswith("/skill"):
        return None
    if len(text) > len("/skill") and not text[len("/skill")].isspace():
        return None
    remaining = text[len("/skill") :].strip()
    return remaining.split(maxsplit=1)[0] if remaining else ""


# 模型调用前处理显式技能
class SkillActivationMiddleware(AgentMiddleware):
    def __init__(self) -> None:
        super().__init__()
        self._skills = {skill.name: skill for skill in load_skills()}

    # 临时加入技能说明
    def _prepare_request(self, request: ModelRequest) -> ModelRequest | AIMessage:
        messages = list(request.messages)
        target_index = next(
            (
                index
                for index in range(len(messages) - 1, -1, -1)
                if isinstance(messages[index], HumanMessage)
                and not messages[index].additional_kwargs.get("hide_from_ui")
                and messages[index].name != "summary"
            ),
            None,
        )
        if target_index is None:
            return request

        state = request.state or {}
        text = _original_user_text(messages[target_index], state.get("uploaded_files"))
        name = _skill_name(text)
        if name is None:
            return request
        if not name:
            return AIMessage(content="请在 /skill 后指定技能名称。")

        skill = self._skills.get(name)
        if skill is None:
            return AIMessage(content=f"技能 {name} 不存在或未启用。")

        try:
            content = Path(skill.path).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return AIMessage(content=f"技能 {name} 的说明文件读取失败，请检查技能文件。")

        # 技能正文只进入本次模型请求
        reminder = HumanMessage(
            content=(
                f'<skill_activation name="{escape(name, quote=True)}">\n'
                "用户已显式启用此技能，请按照以下说明处理本轮请求。\n"
                f'<skill_content encoding="xml-escaped">\n{escape(content, quote=False)}\n</skill_content>\n'
                "</skill_activation>"
            ),
            additional_kwargs={"hide_from_ui": True},
        )
        messages.insert(target_index, reminder)
        return request.override(messages=messages)

    # 包装同步模型调用
    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse | AIMessage:
        prepared = self._prepare_request(request)
        return prepared if isinstance(prepared, AIMessage) else handler(prepared)

    # 包装异步模型调用
    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse | AIMessage:
        prepared = self._prepare_request(request)
        return prepared if isinstance(prepared, AIMessage) else await handler(prepared)
