# 数据库表初始化

from app.schemas.chat.slash import init_slash_commands

from harness.agents.memory.checkpointer import init_checkpointer
from harness.config.app_config import get_app_config
from harness.core.logger import get_logger
from harness.storage import history
from harness.storage.db import init_history_db


logger = get_logger(__name__)


async def initialize_database() -> None:
    # 历史表：chat_thread、chat_turn
    db_path = await init_history_db()

    # 斜杠命令表与初始数据
    await init_slash_commands(db_path)

    # 遗留轮次中断
    history.interrupt_unfinished_turns()
    logger.info("应用表已就绪", path=str(db_path))

    # 检查点表：checkpoints、writes
    checkpointer = await init_checkpointer()
    if checkpointer is None:
        logger.info("检查点记忆已关闭")
    else:
        logger.info(
            "检查点表已就绪",
            path=str(db_path),
            durability=get_app_config().memory.durability,
        )
