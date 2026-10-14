# 技能包配置业务

import re
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import BinaryIO

from py7zr.exceptions import ArchiveError

from app.schemas.config.skill_schema import SkillConfigInfo
from harness.config.app_config import get_app_config
from harness.runtime.db_path import PROJECT_DIR
from harness.skills.installer import InvalidSkillNameError, install, set_enabled, uninstall
from harness.skills.loader import read_skill, resolve_skills_dir
from harness.utils.archive_util import archive_suffix


# 上传大小超限
class SkillUploadTooLargeError(ValueError):
    pass


# 上传技能名称无效
class SkillUploadNameError(ValueError):
    pass


# 安装上传的第三方技能包
def install_skill_config(filename: str | None, source: BinaryIO) -> SkillConfigInfo:
    suffix = archive_suffix(filename or "")
    if suffix is None:
        raise ValueError("不支持的技能压缩包格式")

    config = get_app_config()
    workspace = Path(config.system.workspace_dir)
    if not workspace.is_absolute():
        workspace = PROJECT_DIR / workspace
    temp_dir = workspace.resolve() / "temp"
    if temp_dir.is_symlink() or temp_dir.is_junction():
        raise ValueError("工作空间临时目录不能是链接")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 分块暂存并限制上传大小
    with tempfile.TemporaryDirectory(prefix="skill-upload-", dir=temp_dir) as workdir:
        archive = Path(workdir) / f"upload{suffix}"
        size = 0
        with archive.open("xb") as target:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > config.skills.max_download_bytes:
                    raise SkillUploadTooLargeError("技能压缩包超过大小限制")
                target.write(chunk)
        if size == 0:
            raise ValueError("技能压缩包不能为空")

        try:
            skill = install(archive)
        except InvalidSkillNameError as error:
            raise SkillUploadNameError("技能名称不符合命名规则") from error
        except (ArchiveError, tarfile.TarError, zipfile.BadZipFile, EOFError) as error:
            raise ValueError("技能压缩包损坏") from error

    return SkillConfigInfo(
        name=skill.name,
        description=skill.description,
        source="public",
        enabled=True,
    )


# 扫描已安装的技能包
def list_skill_configs() -> list[SkillConfigInfo]:
    config = get_app_config().skills
    root = resolve_skills_dir()
    if not root.is_dir():
        return []

    found: dict[tuple[str, str], SkillConfigInfo] = {}
    for category in config.categories:
        if category not in {"custom", "public"}:
            continue
        category_dir = root / category
        if category_dir.is_symlink() or category_dir.is_junction() or not category_dir.is_dir():
            continue

        # 普通目录优先于同名的停用目录
        items = sorted(category_dir.iterdir(), key=lambda item: (item.name.startswith("."), item.name))
        for item in items:
            if item.is_symlink() or item.is_junction() or not item.is_dir():
                continue
            enabled = not item.name.startswith(".")
            name = item.name if enabled else item.name[1:]
            if re.fullmatch(config.name_pattern, name) is None:
                continue
            key = (category, name)
            if key in found:
                continue
            skill = read_skill(item, category, expected_name=name)
            if skill is None:
                continue
            found[key] = SkillConfigInfo(
                name=skill.name,
                description=skill.description,
                source=category,
                enabled=enabled,
            )
    return list(found.values())


# 保存第三方技能启停状态
def set_skill_config_enabled(name: str, enabled: bool) -> SkillConfigInfo:
    if "public" not in get_app_config().skills.categories:
        raise ValueError("技能分类未包含 public")
    set_enabled(name, enabled)
    skill = next(
        (item for item in list_skill_configs() if item.source == "public" and item.name == name),
        None,
    )
    if skill is None or skill.enabled != enabled:
        raise ValueError("技能启停后的目录状态无效")
    return skill


# 删除第三方技能包
def delete_skill_config(name: str) -> None:
    uninstall(name)
