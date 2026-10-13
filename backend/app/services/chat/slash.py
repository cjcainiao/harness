# 斜杠命令业务

import asyncio
from collections.abc import Awaitable, Callable

from app.schemas.chat.slash import SlashCommandItem
from harness.config.app_config import get_app_config
from harness.mcp.cache import get_mcp_status
from harness.skills.loader import load_skills
from harness.storage.db import open_history_db


# 一级命令查询
SQL_SELECT_SLASH_COMMANDS = """
SELECT name, label, description, icon_key
FROM slash_command
WHERE enabled = 1 AND (? IS NULL OR name LIKE ? ESCAPE '!')
ORDER BY sort_order ASC, name COLLATE NOCASE ASC
"""


# 查询命令启用状态
SQL_SELECT_ENABLED_COMMAND = """
SELECT 1 FROM slash_command WHERE name = ? AND enabled = 1 LIMIT 1
"""


# 获取斜杠菜单项
async def list_slash_commands(query: str | None = None) -> list[SlashCommandItem]:
    keyword = query.strip() if query else ""
    escaped = keyword.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    pattern = f"%{escaped}%" if escaped else None

    async with open_history_db() as conn:
        async with conn.execute(SQL_SELECT_SLASH_COMMANDS, (pattern, pattern)) as cursor:
            rows = await cursor.fetchall()

    return [SlashCommandItem(**dict(row)) for row in rows]


# 获取技能菜单项
async def list_skill_options(query: str | None = None) -> list[SlashCommandItem]:
    keyword = query.strip().casefold() if query else ""
    skills = await asyncio.to_thread(load_skills)
    return [
        SlashCommandItem(
            name=skill.name,
            label=skill.name,
            description=skill.description,
            icon_key="command",
        )
        for skill in skills
        if not keyword or keyword in skill.name.casefold()
    ]


# 获取 MCP 菜单项
async def list_mcp_options(query: str | None = None) -> list[SlashCommandItem]:
    keyword = query.strip().casefold() if query else ""
    config = get_app_config().mcp
    snapshot = get_mcp_status(config)
    state_labels = {
        "unchecked": "未检查",
        "connected": "已连接",
        "failed": "连接失败",
        "disabled": "已停用",
    }
    return [
        SlashCommandItem(
            name=status.name,
            label=status.name,
            description=f"{state_labels[status.state]} · {len(status.tool_names)} 个工具",
            icon_key="paperclip",
        )
        for status in snapshot.servers
        if not keyword
        or keyword in status.name.casefold()
        or any(keyword in name.casefold() for name in status.tool_names)
    ]


type SlashMenuHandler = Callable[[str | None], Awaitable[list[SlashCommandItem]]]

# 二级菜单处理器
SLASH_MENU_HANDLERS: dict[str, SlashMenuHandler] = {
    "skill": list_skill_options,
    "mcp": list_mcp_options,
}


# 查询命令是否启用
async def is_slash_command_enabled(name: str) -> bool:
    async with open_history_db() as conn:
        async with conn.execute(SQL_SELECT_ENABLED_COMMAND, (name,)) as cursor:
            return await cursor.fetchone() is not None


# 获取当前层级菜单项
async def list_slash_menu(
    command: str | None = None,
    query: str | None = None,
) -> list[SlashCommandItem] | None:
    name = command.strip().casefold() if command else ""
    if not name:
        return await list_slash_commands(query)

    handler = SLASH_MENU_HANDLERS.get(name)
    if handler is None or not await is_slash_command_enabled(name):
        return None
    return await handler(query)
