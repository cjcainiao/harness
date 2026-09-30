# 文本统计工具

from __future__ import annotations

import json
import re

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field


# 汉字匹配，不含标点与数字
_CJK_PATTERN = re.compile(r"[一-鿿]")


# 字数统计参数
class WordCountArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 待统计的文本
    text: str = Field(min_length=1, description="待统计的文本，原样计入统计")


# 统计文本的字符数、词数、汉字数与行数
@tool("word_count", args_schema=WordCountArgs)
def word_count(text: str) -> str:
    """统计一段文本的字符数、词数、汉字数和行数。

    用户要求统计字数、词数或文本规模时使用。词数按空白切分统计，连续中文不切词，中文规模看汉字数。
    文本为空时工具报错，错误原因随工具结果返回。

    Args:
        text: 待统计的文本，原样计入统计。

    Returns:
        JSON 对象字符串，含四个字段：
        - chars: 字符总数，含空白和标点
        - words: 按空白切分出的词数
        - cjk_chars: 汉字数，不含标点和数字
        - lines: 行数，按换行符切分
    """
    result = {
        "chars": len(text),
        "words": len(text.split()),
        "cjk_chars": len(_CJK_PATTERN.findall(text)),
        "lines": len(text.splitlines()) or 1,
    }

    return json.dumps(result, ensure_ascii=False)
