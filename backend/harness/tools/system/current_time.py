# 当前时间工具

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field


# 默认时区
DEFAULT_TIMEZONE = "Asia/Shanghai"


# 当前时间参数
class CurrentTimeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    timezones: list[str] = Field(
        default_factory=lambda: [DEFAULT_TIMEZONE],
        min_length=1,
        description="IANA 时区名称列表，例如 Asia/Shanghai、America/New_York",
    )


# 查询指定时区的当前时间
@tool("current_time", args_schema=CurrentTimeArgs)
def current_time(timezones: list[str] | None = None) -> str:
    """查询一个或多个时区的当前日期、时间和星期。

    用户询问“现在几点”“今天几号”“今天星期几”，或需要同时看几个地区的时间时使用。
    支持任意 IANA 时区，未指定时查询 Asia/Shanghai。

    Args:
        timezones: IANA 时区名称列表，例如 Asia/Shanghai、America/New_York。
            未提供时查询 Asia/Shanghai。

    Returns:
        JSON 数组字符串，每个元素对应一个传入的时区，含三个字段：
        - timezone: 查询使用的时区
        - datetime: ISO 8601 格式的日期时间，精确到秒
        - weekday: 星期几，1 表示周一，7 表示周日
    """
    results: list[dict[str, Any]] = []
    for name in timezones or [DEFAULT_TIMEZONE]:
        try:
            zone = ZoneInfo(name)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"无效的时区：{name}") from error

        now = datetime.now(zone)
        results.append(
            {
                "timezone": name,
                "datetime": now.isoformat(timespec="seconds"),
                "weekday": now.isoweekday(),
            }
        )

    return json.dumps(results, ensure_ascii=False)
