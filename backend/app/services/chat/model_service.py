# 对话模型业务

from app.schemas.chat.model_schema import ModelInfo
from harness.config.app_config import get_app_config


# 获取对话可选模型
def list_chat_models() -> list[ModelInfo]:
    return [
        ModelInfo(
            model_name=model.model_name,
            display_name=model.display_name or model.model_name,
            description=model.description,
            provider=model.provider,
            use=model.use,
            supports_thinking=model.supports_thinking,
            reasoning_levels=model.reasoning_levels,
            supports_vision=model.supports_vision,
            context_window=model.context_window,
        )
        for model in get_app_config().models
    ]
