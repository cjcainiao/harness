# 子代理注册

from __future__ import annotations

import importlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypeVar

from harness.config.app_config import get_app_config
from harness.config.subagents_config import SubagentDefaults, SubagentItem, ToolScope


_T = TypeVar("_T")

# 不限工具时的关键字，与配置里 tools: inherit 同值
INHERIT_TOOLS = "inherit"


# 子代理定义，配置里的 use 指向它；名称由配置登记，这里不重复
@dataclass(frozen=True)
class SubagentDefinition:
    description: str
    system_prompt: str


# 默认值与本条合并后的生效配置
@dataclass(frozen=True)
class SubagentConfig:
    name: str
    description: str
    system_prompt: str
    model: str | None
    max_turns: int
    timeout_seconds: int
    tools: ToolScope
    disallowed_tools: tuple[str, ...]

    # 按可用工具池算最终名单，禁用名单优先
    def enabled_tools(self, pool: Iterable[str]) -> list[str]:
        pool_names = list(pool)
        banned = set(self.disallowed_tools)
        if self.tools == INHERIT_TOOLS:
            return [name for name in pool_names if name not in banned]

        allowed = [name for name in self.tools if name not in banned]
        missing = [name for name in allowed if name not in pool_names]
        if missing:
            raise ValueError(f"子代理 {self.name} 的工具未启用：{'、'.join(missing)}")
        return allowed


# 按 use 取子代理定义
def import_definition(use: str) -> SubagentDefinition:
    module_path, separator, attr_name = str(use).partition(":")
    if not separator or not module_path or not attr_name:
        raise ValueError(f"子代理实现路径格式错误：{use}")
    try:
        module = importlib.import_module(module_path)
    except ImportError as error:
        raise ImportError(f"无法导入子代理模块：{module_path}") from error

    # 定义须是 SubagentDefinition 实例
    definition = getattr(module, attr_name, None)
    if not isinstance(definition, SubagentDefinition):
        raise ValueError(f"子代理定义必须是 SubagentDefinition 实例：{use}")
    return definition


# 取本条生效值，缺失时沿用默认值
def _pick(written: _T | None, fallback: _T) -> _T:
    return fallback if written is None else written


# 合并默认值、本条配置与代码定义
def merge_config(
    item: SubagentItem,
    defaults: SubagentDefaults,
    definition: SubagentDefinition,
) -> SubagentConfig:
    # 禁用名单取并集，去重保序
    banned = tuple(dict.fromkeys([*defaults.disallowed_tools, *(item.disallowed_tools or ())]))
    return SubagentConfig(
        name=item.name,
        description=definition.description,
        system_prompt=definition.system_prompt,
        model=_pick(item.model, defaults.model),
        max_turns=_pick(item.max_turns, defaults.max_turns),
        timeout_seconds=_pick(item.timeout_seconds, defaults.timeout_seconds),
        tools=_pick(item.tools, defaults.tools),
        disallowed_tools=banned,
    )


# 读取配置里的子代理清单，按名称索引
def load_subagent_configs() -> dict[str, SubagentConfig]:
    section = get_app_config().subagents
    if not section.enabled:
        return {}

    configs: dict[str, SubagentConfig] = {}
    for item in section.items:
        # 重名只认靠前那条
        if item.name in configs:
            continue
        configs[item.name] = merge_config(item, section.defaults, import_definition(item.use))
    return configs


# 按名称取一条生效配置
def get_subagent_config(name: str) -> SubagentConfig:
    configs = load_subagent_configs()
    config = configs.get(name)
    if config is None:
        raise ValueError(f"子代理未注册或已停用：{name}")
    return config


# 渲染子代理清单与委派规则，停用或清单为空时不写入提示词
def subagents_section(configs: dict[str, SubagentConfig]) -> str:
    if not configs:
        return ""

    listing = "\n".join(f"- {config.name}：{config.description}" for config in configs.values())
    return (
        "\n\n以下子代理可用 task 工具整块委派，agent 填子代理名称，prompt 写任务：\n"
        f"{listing}\n"
        "\n"
        "委派规则：\n"
        "子代理看不到本轮对话历史，也不会向用户提问，任务里要带上它需要的全部信息。\n"
        "一次回答里可以并行发起多个委派，但每个任务要各自独立，不依赖另一个委派的结果。\n"
        "拿到结果后把结论转述给用户，其中的路径、文件名和数据照抄子代理返回的原文，不要改写或补写它没有给出的内容。\n"
        "委派失败时可以先换个说法重派一次，同一件事最多重派一次；仍然失败就如实说明失败原因，不要替子代理编造结论。\n"
        "合格的委派描述示例：“把 backend/harness 每个子包走一遍，给我一张表，列出包名、py 文件数、是否只有 __init__.py，按包名排序。”"
    )
