# 当前时间工具

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field


# 当前时间参数
class CurrentTimeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    timezone: str = Field(
        default="Asia/Shanghai",
        min_length=1,
        description="IANA 时区名称，例如 Asia/Shanghai 或 UTC",
    )


# 查询指定时区的当前时间
@tool("current_time", args_schema=CurrentTimeArgs)
def current_time(timezone: str = "Asia/Shanghai") -> str:
    """查询当前日期、时间和星期；用户询问现在几点或今天日期时使用。"""
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"无效的时区：{timezone}") from error

    now = datetime.now(zone)
    return json.dumps(
        {
            "timezone": timezone,
            "datetime": now.isoformat(timespec="seconds"),
            "weekday": now.isoweekday(),
        },
        ensure_ascii=False,
    )
