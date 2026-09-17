# DeepSeek 模型实现

from collections.abc import Sequence
from typing import Any

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_deepseek import ChatDeepSeek


# 恢复请求负载中丢失的 DeepSeek 推理内容
def _restore_reasoning_content(
    payload_messages: Sequence[dict[str, Any]],
    original_messages: Sequence[BaseMessage],
) -> None:
    if len(payload_messages) == len(original_messages):
        message_pairs = zip(payload_messages, original_messages)
    else:
        assistant_payloads = [message for message in payload_messages if message.get("role") == "assistant"]
        assistant_messages = [message for message in original_messages if isinstance(message, AIMessage)]
        message_pairs = zip(assistant_payloads, assistant_messages)

    for payload_message, original_message in message_pairs:
        if payload_message.get("role") != "assistant" or not isinstance(original_message, AIMessage):
            continue

        reasoning_content = original_message.additional_kwargs.get("reasoning_content")
        if reasoning_content is not None:
            payload_message["reasoning_content"] = reasoning_content


# DeepSeek 聊天模型实现类
class DeepSeekChatModel(ChatDeepSeek):
    # 允许 LangChain 序列化模型配置
    @classmethod
    def is_lc_serializable(cls) -> bool:
        return True

    # 声明敏感字段对应的环境变量，序列化时不暴露密钥
    @property
    def lc_secrets(self) -> dict[str, str]:
        return {
            "api_key": "DEEPSEEK_API_KEY", # DeepSeek 密钥字段
            "openai_api_key": "DEEPSEEK_API_KEY", # OpenAI 兼容密钥字段
        }

    # 构建请求并恢复多轮对话中的推理内容
    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        original_messages = self._convert_input(input_).to_messages()
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        _restore_reasoning_content(payload.get("messages", []), original_messages)
        return payload
