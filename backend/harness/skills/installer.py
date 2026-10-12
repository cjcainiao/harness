# 技能安装器

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

from ruamel.yaml import YAML

from harness.config.app_config import get_app_config
from harness.runtime.db_path import PROJECT_DIR
from harness.skills.loader import Skill, read_frontmatter, resolve_skills_dir
from harness.utils.archive_util import extract_archive


# 工作空间临时目录
def _temp_dir() -> Path:
    workspace = Path(get_app_config().system.workspace_dir)
    if not workspace.is_absolute():
        workspace = PROJECT_DIR / workspace
    return workspace.resolve() / "temp"


# 第三方技能目录
def public_dir() -> Path:
    return resolve_skills_dir() / "public"


# 校验技能目录名
def _validate_name(name: str) -> None:
    if not isinstance(name, str) or not name or name != name.strip():
        raise ValueError(f"技能 name 必须是非空且无首尾空格的字符串：{name}")
    if re.fullmatch(get_app_config().skills.name_pattern, name) is None:
        raise ValueError(f"技能 name 不符合命名规则：{name}")
    if (
        name in {".", ".."}
        or Path(name).name != name
        or "\\" in name
        or name.endswith((" ", "."))
        or any(char in '<>:"|?*' or ord(char) < 32 for char in name)
    ):
        raise ValueError(f"技能 name 不能用作目录名：{name}")


# 读取技能主文件元数据
def _skill_metadata(skill_file: Path) -> tuple[str, str]:
    config = get_app_config().skills
    try:
        with skill_file.open("rb") as source:
            raw_bytes = source.read(config.max_skill_file_bytes + 1)
    except OSError as error:
        raise ValueError(f"技能主文件读取失败：{skill_file}") from error
    if len(raw_bytes) > config.max_skill_file_bytes:
        raise ValueError(f"技能主文件超过 {config.max_skill_file_bytes} 字节：{skill_file}")
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"技能主文件无法按 UTF-8 读取：{skill_file}") from error

    frontmatter = read_frontmatter(raw)
    if frontmatter is None:
        raise ValueError(f"技能主文件缺少 YAML frontmatter：{skill_file}")

    try:
        meta = YAML(typ="safe").load(frontmatter)
    except Exception as error:
        raise ValueError(f"技能主文件 YAML 解析失败：{skill_file}：{error}") from error
    if not isinstance(meta, dict):
        raise ValueError(f"技能主文件 frontmatter 必须是键值结构：{skill_file}")

    name = meta.get("name")
    description = meta.get("description")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"技能 name 必须是非空字符串：{skill_file}")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"技能 description 必须是非空字符串：{skill_file}")

    name = name.strip()
    description = description.strip()
    _validate_name(name)
    if len(description) > config.description_limit:
        raise ValueError(f"技能 description 超过 {config.description_limit} 字：{skill_file}")

    return name, description


# 校验解压后的技能目录
def validate_skill(skill_path: str | Path, *, expected_name: str | None = None) -> Skill:
    config = get_app_config().skills
    skill_dir = Path(skill_path)
    if skill_dir.is_symlink() or skill_dir.is_junction():
        raise ValueError(f"技能目录不能是链接：{skill_dir}")
    skill_dir = skill_dir.resolve()
    if not skill_dir.is_dir():
        raise ValueError(f"技能目录不存在：{skill_dir}")

    skill_file = skill_dir / config.file
    if not skill_file.is_file():
        raise ValueError(f"技能目录缺少主文件：{skill_file}")

    for entry in skill_dir.rglob("*"):
        if entry.is_symlink() or entry.is_junction():
            raise ValueError(f"技能包包含链接：{entry}")
        if entry != skill_file and entry.name == config.file:
            raise ValueError(f"技能包包含嵌套主文件：{entry}")

    name, description = _skill_metadata(skill_file)
    directory_name = expected_name if expected_name is not None else skill_dir.name
    if name != directory_name:
        raise ValueError(f"技能 name 与目录名不一致：{name}、{directory_name}")

    return Skill(name=name, description=description, path=skill_file.resolve().as_posix(), source="public")


# 定位压缩包中的技能目录
def _find_skill_dir(extracted: Path) -> Path:
    skill_file = get_app_config().skills.file
    candidates = [item.parent for item in extracted.rglob(skill_file) if item.is_file()]
    if len(candidates) != 1:
        raise ValueError(f"压缩包必须恰好包含一个技能，找到 {len(candidates)} 个：{extracted}")
    return candidates[0]


# 检查各分类中的同名技能
def _check_name_conflict(name: str, *, exclude_category: str | None = None) -> None:
    root = resolve_skills_dir()
    categories = set(get_app_config().skills.categories) | {"public"}
    for category in categories:
        if category == exclude_category:
            continue
        for candidate in (root / category / name, root / category / f".{name}"):
            if candidate.exists() or candidate.is_symlink() or candidate.is_junction():
                raise FileExistsError(f"已存在同名技能：{candidate}")


# 安装本地技能压缩包
def install(skill_archive_path: str | Path) -> Skill:
    config = get_app_config().skills
    if "public" not in config.categories:
        raise ValueError("技能分类未包含 public，无法安装第三方技能")

    archive = Path(skill_archive_path)
    if archive.is_symlink() or archive.is_junction():
        raise ValueError(f"技能压缩包不能是链接：{archive}")
    if not archive.is_file():
        raise FileNotFoundError(f"技能压缩包不存在：{archive}")
    if archive.stat().st_size > config.max_download_bytes:
        raise ValueError(f"技能压缩包超过 {config.max_download_bytes} 字节：{archive}")

    temp_dir = _temp_dir()
    if temp_dir.is_symlink() or temp_dir.is_junction():
        raise ValueError(f"工作空间临时目录不能是链接：{temp_dir}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 临时区复制与解压
    with tempfile.TemporaryDirectory(prefix="skill-", dir=temp_dir) as workdir:
        staged_archive = Path(workdir) / archive.name
        copied = 0
        with archive.open("rb") as source, staged_archive.open("xb") as target:
            while chunk := source.read(1024 * 1024):
                copied += len(chunk)
                if copied > config.max_download_bytes:
                    raise ValueError(f"技能压缩包超过 {config.max_download_bytes} 字节：{archive}")
                target.write(chunk)
        extracted = extract_archive(
            staged_archive,
            max_entries=config.max_archive_entries,
            max_unpacked_bytes=config.max_unpacked_bytes,
        )
        skill_dir = _find_skill_dir(extracted)
        name, _ = _skill_metadata(skill_dir / config.file)
        # 归一化技能目录名
        if skill_dir.name != name:
            if not skill_dir.resolve().is_relative_to(Path(workdir).resolve()):
                raise ValueError(f"技能目录超出临时目录：{skill_dir}")
            normalized_root = Path(tempfile.mkdtemp(prefix="normalized-", dir=workdir))
            normalized = normalized_root / name
            skill_dir.rename(normalized)
            skill_dir = normalized

        skill = validate_skill(skill_dir)
        _check_name_conflict(skill.name)

        target_root = public_dir()
        if target_root.is_symlink() or target_root.is_junction():
            raise ValueError(f"技能安装目录不能是链接：{target_root}")
        target_root.mkdir(parents=True, exist_ok=True)
        # 同级暂存后落盘
        staging = Path(tempfile.mkdtemp(prefix=".install-", dir=target_root))
        try:
            shutil.copytree(skill_dir, staging, dirs_exist_ok=True)
            _check_name_conflict(skill.name)
            installed_dir = target_root / skill.name
            staging.rename(installed_dir)
        finally:
            if staging.exists():
                shutil.rmtree(staging)

        return Skill(
            name=skill.name,
            description=skill.description,
            path=(installed_dir / config.file).resolve().as_posix(),
            source="public",
        )


# 查找第三方技能目录
def _public_skill_paths(name: str) -> tuple[Path, Path, Path]:
    _validate_name(name)
    root = public_dir()
    if root.is_symlink() or root.is_junction():
        raise ValueError(f"技能安装目录不能是链接：{root}")

    enabled = root / name
    disabled = root / f".{name}"
    has_enabled = enabled.exists() or enabled.is_symlink() or enabled.is_junction()
    has_disabled = disabled.exists() or disabled.is_symlink() or disabled.is_junction()
    if has_enabled and has_disabled:
        raise FileExistsError(f"技能同时存在启用和停用目录：{enabled}、{disabled}")
    if not has_enabled and not has_disabled:
        raise FileNotFoundError(f"第三方技能不存在：{name}")

    current = enabled if has_enabled else disabled
    if current.is_symlink() or current.is_junction():
        raise ValueError(f"技能目录不能是链接：{current}")
    if not current.is_dir():
        raise ValueError(f"技能路径不是目录：{current}")
    return current, enabled, disabled


# 卸载第三方技能
def uninstall(name: str) -> None:
    current, _, _ = _public_skill_paths(name)
    shutil.rmtree(current)


# 启用或停用技能
def set_enabled(name: str, enabled: bool) -> None:
    current, active_dir, inactive_dir = _public_skill_paths(name)
    target = active_dir if enabled else inactive_dir
    if current == target:
        return
    if enabled:
        validate_skill(current, expected_name=name)
        _check_name_conflict(name, exclude_category="public")
    current.rename(target)
