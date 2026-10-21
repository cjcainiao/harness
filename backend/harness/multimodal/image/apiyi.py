# API易图像服务

from harness.multimodal.image.openai import OpenAIImageProvider


class APIYIImageProvider(OpenAIImageProvider):
    generation_url = "https://api.apiyi.com/v1/images/generations"
    edit_url = "https://api.apiyi.com/v1/images/edits"
