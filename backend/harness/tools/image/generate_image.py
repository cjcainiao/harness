# 图片生成工具

from __future__ import annotations

import asyncio
import base64
import json
from io import BytesIO
from typing import Literal

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field

from harness.multimodal.image.generation import IMAGE_PROVIDERS, request_image
from harness.tools.image.generated_files import save_generated_image
from harness.tools.image.view_image import load_uploaded_image
from harness.tools.tool_settings import get_tool_settings


# 图片生成参数
class GenerateImageArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    # 画面描述
    prompt: str = Field(min_length=1, description="要生成的图片内容、风格与构图描述。")

    # 图片画幅
    aspect_ratio: Literal["1:1", "16:9", "9:16"] | None = Field(
        default=None, description="图片画幅，可选 1:1、16:9 或 9:16；省略时使用系统默认画幅。"
    )

    # 当前会话的参考图片
    reference_image_id: str | None = Field(
        default=None, description="当前会话已上传图片的文件标识；仅在用户要求参考图片生成或编辑时传入。"
    )

    # 当前工具运行环境
    runtime: ToolRuntime


# 校验图片服务配置
def _settings() -> dict:
    settings = get_tool_settings("generate_image")
    required_text = ("provider", "api_key", "model")
    for name in required_text:
        if not isinstance(settings.get(name), str) or not settings[name].strip():
            raise ValueError(f"generate_image 未配置 {name}")
    provider = settings["provider"].strip().lower()
    if provider not in IMAGE_PROVIDERS:
        raise ValueError("generate_image 的 provider 不受支持")
    timeout = settings.get("timeout_seconds")
    max_bytes = settings.get("max_image_bytes")
    max_pixels = settings.get("max_image_pixels")
    max_prompt = settings.get("max_prompt_chars")
    max_reference_bytes = settings.get("max_reference_image_bytes")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("generate_image 的 timeout_seconds 必须大于 0")
    for name, value in (
        ("max_image_bytes", max_bytes),
        ("max_image_pixels", max_pixels),
        ("max_prompt_chars", max_prompt),
        ("max_reference_image_bytes", max_reference_bytes),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"generate_image 的 {name} 必须是正整数")
    ratios = ("1:1", "16:9", "9:16")
    if settings.get("default_aspect_ratio") not in ratios:
        raise ValueError("generate_image 未正确配置 default_aspect_ratio")
    return {**settings, "provider": provider}


# 校验参考图并编码给图片服务
def _reference_image_data_url(thread_id: str, file_id: str, max_bytes: int) -> str:
    source, mime_type, data = load_uploaded_image(thread_id, file_id)
    if len(data) > max_bytes:
        raise ValueError(f"参考图片超过大小限制：{source}")
    try:
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            if width > 8000 or height > 8000 or max(width, height) > 10 * min(width, height):
                raise ValueError(f"参考图片尺寸或长宽比超出服务限制：{source}")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError(f"参考图片内容无效：{source}") from error
    return f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"

# 根据画面描述生成一张图片
@tool("generate_image", args_schema=GenerateImageArgs)
async def generate_image(
    prompt: str,
    runtime: ToolRuntime,
    aspect_ratio: Literal["1:1", "16:9", "9:16"] | None = None,
    reference_image_id: str | None = None,
) -> str:
    """根据文字描述生成图片，也可参考当前会话上传的图片进行编辑。

    用户明确要求画图、生成图片、参考上传图片改图时使用。参考图片无效或生成失败时工具报错。

    Args:
        prompt: 要生成的图片内容、风格与构图描述。
        aspect_ratio: 图片画幅，可选 1:1、16:9 或 9:16；省略时使用系统默认画幅。
        reference_image_id: 当前会话已上传图片的文件标识；仅在用户要求参考图片生成或编辑时传入。

    Returns:
        JSON 对象字符串，包含 image_id 图片标识、mime_type 图片格式、width 宽度和 height 高度。
    """
    context = runtime.context or {}
    thread_id = context.get("thread_id") or (runtime.config or {}).get("configurable", {}).get("thread_id")
    if not isinstance(thread_id, str) or not thread_id:
        raise ValueError("缺少 thread_id，无法保存生成图片")
    settings = _settings()
    prompt = prompt.strip()
    if not prompt or len(prompt) > settings["max_prompt_chars"]:
        raise ValueError("图片描述为空或超过长度限制")
    ratio = aspect_ratio or settings["default_aspect_ratio"]
    if ratio not in ("1:1", "16:9", "9:16"):
        raise ValueError("不支持的图片画幅")
    reference_image_data_url = None
    if reference_image_id is not None:
        reference_image_data_url = await asyncio.to_thread(
            _reference_image_data_url, thread_id, reference_image_id, settings["max_reference_image_bytes"]
        )
    data = await request_image(prompt, ratio, settings, reference_image_data_url)
    stored = await asyncio.to_thread(
        save_generated_image,
        thread_id,
        data,
        settings["max_image_bytes"],
        settings["max_image_pixels"],
    )
    return json.dumps(
        {
            "image_id": stored.image_id,
            "mime_type": stored.mime_type,
            "width": stored.width,
            "height": stored.height,
        },
        ensure_ascii=False,
    )
