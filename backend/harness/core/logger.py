# 日志

import copy
import json
import logging
import queue
import sys
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from typing import Any

import structlog

_listener: QueueListener | None = None

class _StructlogQueueHandler(QueueHandler):
    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        return copy.copy(record)

# 日志级别字符串转 logging 常量
def _log_level(level: str) -> int:
    return getattr(logging, level.strip().upper(), logging.INFO)

# 控制台与文件共用的处理链
def _shared_processors() -> list[Any]:
    return [
        # 合并 request_id、conversation_id 等上下文变量
        structlog.contextvars.merge_contextvars,
        # 添加 logger 名称
        structlog.stdlib.add_logger_name,
        # 添加日志级别
        structlog.stdlib.add_log_level,
        # 添加时间
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        # 允许 %s 占位符参数
        structlog.stdlib.PositionalArgumentsFormatter(),
        # 渲染 stack_info=True
        structlog.processors.StackInfoRenderer(),
        # 渲染异常堆栈
        structlog.processors.format_exc_info,
        # 把 logging 的 extra 字段带进事件字典
        structlog.stdlib.ExtraAdder(),
    ]

# 配置日志：控制台彩色，文件结构化 JSON，写盘走后台线程
def configure_logging(
    level: str = "INFO",
    env: str = "dev",
    log_dir: str | Path | None = None,
    filename: str = "harness.log",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 7,
    console: bool | None = None,
    file: bool = True,
    queue_logs: bool = True,
) -> None:
    global _listener

    log_level = _log_level(level)

    # 日志目录：默认 backend/logs，相对路径按后端项目根解析，都不受启动目录影响
    project_dir = Path(__file__).resolve().parents[2]
    if log_dir is None:
        path = project_dir / "logs"
    else:
        path = Path(log_dir)
        if not path.is_absolute():
            path = project_dir / path
    if file:
        path.mkdir(parents=True, exist_ok=True)

    # 生产环境默认不输出控制台，省掉彩色渲染与一次写终端
    if console is None:
        console = env != "prod"

    shared = _shared_processors()

    # 配置 structlog，链首先按级别过滤，被拦掉的日志不再走后面的处理器
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 配置 Python 标准 logging，重复调用不会叠加 handler 与监听线程
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    if _listener is not None:
        _listener.stop()
        _listener = None
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    handlers: list[logging.Handler] = []

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=shared,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(colors=True),
                ],
            )
        )
        handlers.append(console_handler)

    if file:
        file_handler = RotatingFileHandler(
            path / filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=shared,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.processors.JSONRenderer(
                        serializer=lambda obj, **kw: json.dumps(obj, ensure_ascii=False, **kw)
                    ),
                ],
            )
        )
        handlers.append(file_handler)

    if queue_logs and handlers:
        # 调用方只做入队，渲染与写盘交给后台线程
        log_queue: queue.SimpleQueue = queue.SimpleQueue()
        root_logger.addHandler(_StructlogQueueHandler(log_queue))
        _listener = QueueListener(log_queue, *handlers, respect_handler_level=True)
        _listener.start()
    else:
        for handler in handlers:
            root_logger.addHandler(handler)

    # 控制第三方库日志数量
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if log_level == logging.DEBUG else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

# 关闭日志，把队列里剩余的记录写完
def shutdown_logging() -> None:
    global _listener
    if _listener is not None:
        _listener.stop()
        _listener = None

# 获取 structlog 日志器
def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
