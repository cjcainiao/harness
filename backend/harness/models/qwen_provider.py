# 千问模型实现

from typing import Any

from langchain_qwq import ChatQwen


# 千问聊天模型实现类
class QwenChatModel(ChatQwen):
    # 允许 LangChain 序列化模型配置
    @classmethod
    def is_lc_serializable(cls) -> bool:
        return True

    # 映射推理强度为模型参数
    @staticmethod
    def reasoning_model_kwargs(effort: str) -> dict[str, Any]:
        return {"reasoning_effort": effort}
