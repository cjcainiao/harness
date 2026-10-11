# 斜杠命令结构与表初始化

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from harness.storage.db import open_history_db


# 命令菜单项
class SlashCommandItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="菜单项名称，不含斜杠")
    label: str = Field(description="菜单显示名称")
    description: str = Field(description="菜单说明")
    icon_key: str = Field(description="前端图标标识")


# 初始化命令表与初始数据
async def init_slash_commands(db_path: Path) -> None:
    async with open_history_db(db_path) as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS slash_command (
                -- 命令名称，不含斜杠
                name TEXT NOT NULL COLLATE NOCASE PRIMARY KEY,
                -- 菜单显示名称
                label TEXT NOT NULL,
                -- 菜单说明
                description TEXT NOT NULL,
                -- 前端图标标识
                icon_key TEXT NOT NULL DEFAULT 'command',
                -- 启用状态，取值 0 / 1
                enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                -- 菜单排序
                sort_order INTEGER NOT NULL DEFAULT 0,
                -- 创建时间，ISO-8601 UTC
                created_at TEXT NOT NULL,
                -- 修改时间，ISO-8601 UTC
                updated_at TEXT NOT NULL
            );
            """
        )
        await conn.execute(
            """
            INSERT INTO slash_command (
                name, label, description, icon_key, enabled, sort_order, created_at, updated_at
            )
            VALUES
                (
                    'skill', '技能', '搜索并选择可用技能', 'command', 1, 0,
                    strftime('%Y-%m-%dT%H:%M:%SZ', 'now'),
                    strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                ),
                (
                    'mcp', 'MCP', '显示 MCP 服务器状态', 'paperclip', 1, 0,
                    strftime('%Y-%m-%dT%H:%M:%SZ', 'now'),
                    strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                )
            ON CONFLICT (name) DO NOTHING;
            """
        )
        await conn.commit()
