# 技能按需发现工具

from __future__ import annotations

import json
import re
from collections.abc import Sequence

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from harness.skills.loader import Skill, load_skills
from harness.tools.tool_settings import get_tool_settings


# 编译检索词，无效正则按普通文字匹配
def _compile_query(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        return re.compile(re.escape(pattern), re.IGNORECASE)


# 检索技能目录
def _search(query: str, limit: int, skills: Sequence[Skill]) -> list[Skill]:
    if limit <= 0:
        raise ValueError(f"返回条数上限必须为正数：{limit}")

    target = query.strip()
    if not target:
        return []

    # 按完整名称精确选择，不截断
    if target.startswith("select:"):
        wanted = {name.strip() for name in target[7:].split(",")}
        return [skill for skill in skills if skill.name in wanted]

    # 先限定名称，再按剩余检索词排序
    if target.startswith("+"):
        parts = target[1:].split(None, 1)
        if not parts:
            return []
        required = parts[0].casefold()
        matches = [skill for skill in skills if required in skill.name.casefold()]
        if len(parts) > 1:
            regex = _compile_query(parts[1])
            matches.sort(
                key=lambda skill: len(regex.findall(f"{skill.name} {skill.description}")),
                reverse=True,
            )
        return matches[:limit]

    # 名称命中优先于仅描述命中
    regex = _compile_query(target)
    scored = [
        (2 if regex.search(skill.name) else 1, skill)
        for skill in skills
        if regex.search(f"{skill.name} {skill.description}")
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [skill for _, skill in scored[:limit]]


# 技能发现参数
class DescribeSkillArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 技能名称或检索关键词
    name: str = Field(
        min_length=1,
        description="查询：select:技能名1,技能名2 精确选择；+名称关键词 说明关键词 限定名称并排序；其他内容按名称和描述做不区分大小写的正则匹配",
    )


# 查找可用技能
@tool("describe_skill", args_schema=DescribeSkillArgs)
def describe_skill(name: str) -> str:
    """按名称或关键词查找可用技能。

    需要了解某个技能的用途与说明文档位置时使用。select: 可按准确名称一次取回多个技能；
    + 开头时先按名称关键词筛选，再用剩余内容排序；其他查询匹配名称和描述。
    普通查询支持不区分大小写的正则表达式，无效正则按普通文字匹配。
    命中后用 read_file 读取返回的说明文档路径；本工具不返回技能正文。
    没有命中时返回空数组；配置中的上限无效时工具报错。

    Args:
        name: 查询：select:技能名1,技能名2 精确选择；+名称关键词 说明关键词 限定名称并排序；其他内容按名称和描述做不区分大小写的正则匹配。

    Returns:
        JSON 数组字符串，每个元素包含三个字段：
        - name: 技能名称
        - description: 技能用途与适用场景
        - path: SKILL.md 的本地绝对路径，可传入 read_file 的 paths 列表
    """
    limit = get_tool_settings("describe_skill").get("default_max_results")
    if limit is None:
        raise ValueError("describe_skill 未配置返回上限：settings.default_max_results 缺失")

    skills = _search(name, int(limit), load_skills())
    return json.dumps(
        [
            {"name": skill.name, "description": skill.description, "path": skill.path}
            for skill in skills
        ],
        ensure_ascii=False,
    )
