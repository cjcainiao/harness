# 技能包结构自检

from __future__ import annotations

import re
import sys
from pathlib import Path

from ruamel.yaml import YAML


# 技能根目录
SKILLS_DIR = Path(__file__).resolve().parents[2]

# 主文件名
SKILL_FILE = "SKILL.md"

# 必填字段
REQUIRED_FIELDS = ("name", "description")

# 技能名字符集
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# 描述字数上限
DESCRIPTION_LIMIT = 1024

# 主文件建议行数
BODY_SOFT_LIMIT = 60

# 可选目录
OPTIONAL_DIRS = ("scripts", "references", "assets")


# 取 frontmatter 文本
def read_frontmatter(raw: str) -> str | None:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:index])
    return None


# 校验单个技能包
def check_skill(skill_file: Path, yaml_reader: YAML) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    notes: list[str] = []
    skill_dir = skill_file.parent
    raw = skill_file.read_text(encoding="utf-8")

    frontmatter = read_frontmatter(raw)
    if frontmatter is None:
        return [f"{skill_dir.name}: 缺少 frontmatter 区块"], notes

    try:
        meta = yaml_reader.load(frontmatter) or {}
    except Exception as error:
        return [f"{skill_dir.name}: frontmatter 解析失败 {error}"], notes

    if not isinstance(meta, dict):
        return [f"{skill_dir.name}: frontmatter 不是键值结构"], notes

    for field in REQUIRED_FIELDS:
        if not str(meta.get(field, "")).strip():
            problems.append(f"{skill_dir.name}: 必填字段 {field} 缺失或为空")

    name = str(meta.get("name", ""))
    if name and name != skill_dir.name:
        problems.append(f"{skill_dir.name}: name 与目录名不一致，取值为 {name}")
    if name and not NAME_PATTERN.match(name):
        problems.append(f"{skill_dir.name}: name 须为小写字母、数字与连字符")

    description = str(meta.get("description", ""))
    if len(description) > DESCRIPTION_LIMIT:
        problems.append(f"{skill_dir.name}: description {len(description)} 字，超上限 {DESCRIPTION_LIMIT}")

    extra_keys = [key for key in meta if key not in REQUIRED_FIELDS]
    if extra_keys:
        notes.append(f"{skill_dir.name}: frontmatter 有多余字段 {extra_keys}")

    body_lines = len(raw.splitlines())
    if body_lines > BODY_SOFT_LIMIT:
        notes.append(f"{skill_dir.name}: SKILL.md 共 {body_lines} 行，建议细节移入 references/")

    for entry in OPTIONAL_DIRS:
        if (skill_dir / entry).is_dir():
            notes.append(f"{skill_dir.name}: 含 {entry}/")

    return problems, notes


# 扫描技能根目录
def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"技能根目录不存在：{SKILLS_DIR}")
        return 1

    skill_files = sorted(SKILLS_DIR.rglob(SKILL_FILE))
    if not skill_files:
        print(f"未扫到任何技能包：{SKILLS_DIR}")
        return 1

    yaml_reader = YAML(typ="safe")
    problems: list[str] = []
    notes: list[str] = []
    for skill_file in skill_files:
        found, infos = check_skill(skill_file, yaml_reader)
        problems.extend(found)
        notes.extend(infos)

    print(f"技能根目录：{SKILLS_DIR}")
    print(f"技能包数量：{len(skill_files)}")
    for note in notes:
        print(f"  · {note}")
    for problem in problems:
        print(f"  ✗ {problem}")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
