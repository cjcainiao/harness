# 网页搜索工具

from __future__ import annotations

import json

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from harness.tools.tool_settings import get_tool_settings


# 网页搜索参数
class WebSearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 搜索关键词
    query: str = Field(min_length=1, description="搜索关键词。")


# 搜索公开网页
@tool("web_search", args_schema=WebSearchArgs)
def web_search(query: str) -> str:
    """搜索公开网页并返回相关结果。

    需要查找公开网页时使用百度千帆搜索。配置缺失或请求失败时工具报错。

    Args:
        query: 搜索关键词。

    Returns:
        JSON 数组字符串，每项包含 title、url 和 snippet。
    """
    # 校验搜索参数
    query = query.strip()
    if not query:
        raise ValueError("网页搜索关键词不能为空")
    if sum(2 if ord(char) > 127 else 1 for char in query) > 72:
        raise ValueError("百度千帆搜索关键词不能超过 72 个字符，汉字按两个字符计算")

    # 读取服务配置
    settings = get_tool_settings("web_search")
    base_url = settings.get("base_url")
    api_key = settings.get("api_key")
    timeout_seconds = settings.get("timeout_seconds")
    top_k = settings.get("top_k")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("web_search 未配置 base_url")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("web_search 未配置 api_key")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or timeout_seconds <= 0
    ):
        raise ValueError("web_search 的 timeout_seconds 必须大于 0")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 50:
        raise ValueError("web_search 的 top_k 必须是 1 到 50 之间的整数")

    # 限定千帆搜索接口
    base_url = base_url.strip().rstrip("/")
    if base_url == "https://qianfan.baidubce.com/v2":
        endpoint = f"{base_url}/ai_search/web_search"
    elif base_url == "https://qianfan.baidubce.com/v2/ai_search/web_search":
        endpoint = base_url
    else:
        raise ValueError("web_search 的 base_url 必须是百度千帆搜索服务地址")

    # 请求百度千帆
    try:
        response = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key.strip()}"},
            json={
                "messages": [{"role": "user", "content": query}],
                "search_source": "baidu_search_v2",
                "resource_type_filter": [{"type": "web", "top_k": top_k}],
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise ValueError(f"百度千帆网页搜索失败：HTTP {error.response.status_code}") from error
    except httpx.RequestError as error:
        raise ValueError("百度千帆网页搜索请求失败") from error

    # 解析网页结果
    try:
        data = response.json()
    except ValueError as error:
        raise ValueError("百度千帆网页搜索返回的内容不是 JSON") from error
    if not isinstance(data, dict):
        raise ValueError("百度千帆网页搜索返回格式无效")
    code = data.get("code")
    if code not in (None, 0, "0"):
        raise ValueError(f"百度千帆网页搜索失败：错误码 {code}")
    references = data.get("references") or []
    if not isinstance(references, list):
        raise ValueError("百度千帆网页搜索缺少 references")

    results: list[dict[str, str]] = []
    for item in references:
        if not isinstance(item, dict) or item.get("type", "web") != "web":
            continue
        title = item.get("title")
        url = item.get("url")
        if not isinstance(title, str) or not title or not isinstance(url, str) or not url:
            continue
        snippet = item.get("snippet") or item.get("content") or ""
        results.append(
            {"title": title, "url": url, "snippet": snippet if isinstance(snippet, str) else ""}
        )
        if len(results) >= top_k:
            break

    return json.dumps(results, ensure_ascii=False)
