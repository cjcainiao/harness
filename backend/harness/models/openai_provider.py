# OpenAI 模型实现

from typing import Any

from langchain_openai import ChatOpenAI


# OpenAI 兼容聊天模型实现类
class OpenAIChatModel(ChatOpenAI):
    # 映射推理强度为模型参数
    @staticmethod
    def reasoning_model_kwargs(effort: str) -> dict[str, Any]:
        return {"reasoning_effort": effort}
