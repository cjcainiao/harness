# 技能加载器

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

from harness.config.app_config import get_app_config
from harness.core.logger import get_logger
from harness.runtime.db_path import PROJECT_DIR


logger = get_logger(__name__)


# 加载 yaml
_yaml_safe = YAML(typ="safe")


# 技能条目
@dataclass(frozen=True)
class Skill:
    # 技能名
    name: str
    # 技能描述
    description: str
    # 主文件绝对路径
    path: str
    # 所属分类
    source: str


# 取 frontmatter 文本
def read_frontmatter(raw: str) -> str | None:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    # 找闭合的结束线
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index])
    return None


# 解析单个技能包
def read_skill(skill_dir: Path, source: str) -> Skill | None:
    config = get_app_config().skills

    skill_file = skill_dir / config.file
    if not skill_file.is_file():
        logger.warning("技能目录缺少主文件，跳过", dir=str(skill_dir), file=config.file)
        return None

    try:
        raw = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        logger.warning("技能主文件读取失败，跳过", path=str(skill_file), error=str(error))
        return None

    frontmatter = read_frontmatter(raw)
    if frontmatter is None:
        logger.warning("技能缺少 frontmatter，跳过", path=str(skill_file))
        return None

    try:
        meta = _yaml_safe.load(frontmatter) or {}
    except Exception as error:
        logger.warning("技能 frontmatter 解析失败，跳过", path=str(skill_file), error=str(error))
        return None

    if not isinstance(meta, dict):
        logger.warning("技能 frontmatter 不是键值结构，跳过", path=str(skill_file))
        return None

    name = str(meta.get("name") or "").strip()
    description = str(meta.get("description") or "").strip()
    if not name or not description:
        logger.warning("技能缺少 name 或 description，跳过", path=str(skill_file))
        return None
    if name != skill_dir.name:
        logger.warning("技能 name 与目录名不一致，跳过", name=name, dir=skill_dir.name)
        return None
    if not re.match(config.name_pattern, name):
        logger.warning("技能 name 字符集不合规，跳过", name=name, pattern=config.name_pattern)
        return None
    if len(description) > config.description_limit:
        logger.warning(
            "技能 description 超字数上限，跳过",
            name=name,
            length=len(description),
            limit=config.description_limit,
        )
        return None

    return Skill(
        name=name,
        description=description,
        path=skill_file.resolve().as_posix(),
        source=source,
    )


# 解析技能根目录绝对路径
def resolve_skills_dir() -> Path:
    target = Path(get_app_config().skills.dir)
    if not target.is_absolute():
        target = PROJECT_DIR / target
    return target


# 扫描分类目录，取技能名单
def load_skills() -> list[Skill]:
    config = get_app_config().skills
    if not config.enabled:
        return []

    root = resolve_skills_dir()
    if not root.is_dir():
        logger.warning("技能根目录不存在", dir=str(root))
        return []

    found: dict[str, Skill] = {}
    for category in config.categories:
        category_dir = root / category
        if not category_dir.is_dir():
            continue

        for item in sorted(category_dir.iterdir()):
            # 符号链接目录不跟随
            if item.is_symlink():
                logger.warning("技能目录是符号链接，跳过", dir=str(item))
                continue
            # 点前缀目录为已停用
            if not item.is_dir() or item.name.startswith("."):
                continue

            skill = read_skill(item, category)
            if skill is None:
                continue

            shadowed = found.get(skill.name)
            if shadowed is not None:
                logger.warning(
                    "技能重名，按分类优先级保留先出现的",
                    name=skill.name,
                    keep=shadowed.source,
                    drop=category,
                )
                continue
            found[skill.name] = skill

    return list(found.values())


# 拼进提示词的技能名单
def skills_section(skills: list[Skill], *, describe_skill_enabled: bool) -> str:
    if not skills:
        return ""

    # 技能发现工具可用时只列名称
    if describe_skill_enabled:
        names = "\n".join(f"- {skill.name}" for skill in skills)
        return (
            "\n\n以下是可用技能名称。任务需要某个技能时，先调用 describe_skill 查询用途和说明文档路径，"
            "确认适用后再用 read_file 读取说明文档并按文档执行：\n"
            f"<skill_index>\n{names}\n</skill_index>"
        )

    # 技能发现工具不可用时列出完整元数据
    listing = "\n".join(
        f"- {skill.name}: {skill.description}\n  说明文档：{skill.path}" for skill in skills
    )
    return (
        "\n\n以下技能按需使用，任务命中某个技能时，先用 read_file 读取该技能的说明文档再按文档执行：\n"
        f"{listing}"
    )
