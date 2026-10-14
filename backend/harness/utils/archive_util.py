# 压缩包工具

from __future__ import annotations

import shutil
import stat
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable

import py7zr


_ARCHIVE_SUFFIXES = (
    ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz",
    ".tar", ".zip", ".skill", ".7z",
)


# 识别压缩包格式
def archive_suffix(filename: str) -> str | None:
    name = filename.lower()
    return next((suffix for suffix in _ARCHIVE_SUFFIXES if name.endswith(suffix)), None)


# 校验压缩包内的路径
def _member_parts(name: str) -> tuple[str, ...]:
    if not name or name.startswith(("/", "\\")) or "\\" in name:
        raise ValueError(f"压缩包包含不安全路径：{name}")
    parts = name.rstrip("/").split("/")
    for part in parts:
        if (
            part in {"", ".", ".."}
            or part.endswith((" ", "."))
            or any(char in '<>:"|?*' or ord(char) < 32 for char in part)
        ):
            raise ValueError(f"压缩包包含不安全路径：{name}")
    return tuple(parts)


# 校验压缩包清单
def _check_members(
    members: Iterable[tuple[str, bool, int]],
    max_entries: int | None,
    max_unpacked_bytes: int | None,
) -> None:
    seen: dict[tuple[str, ...], bool] = {}
    total = 0
    for count, (name, is_dir, size) in enumerate(members, start=1):
        if max_entries is not None and count > max_entries:
            raise ValueError(f"压缩包文件数量超过 {max_entries}")
        if size < 0:
            raise ValueError(f"压缩包文件大小无效：{name}")
        total += size
        if max_unpacked_bytes is not None and total > max_unpacked_bytes:
            raise ValueError(f"压缩包解压大小超过 {max_unpacked_bytes} 字节")
        # 跨平台重名路径校验
        key = tuple(part.casefold() for part in _member_parts(name))
        if key in seen:
            raise ValueError(f"压缩包包含重名路径：{name}")
        seen[key] = is_dir

    for key in seen:
        if any(seen.get(key[:length]) is False for length in range(1, len(key))):
            raise ValueError(f"压缩包文件与目录冲突：{'/'.join(key)}")


# 解压压缩包
def extract_archive(
    file_path: str | Path,
    *,
    max_entries: int | None = None,
    max_unpacked_bytes: int | None = None,
) -> Path:
    archive = Path(file_path).resolve()
    if not archive.is_file():
        raise FileNotFoundError(f"压缩包不存在：{archive}")

    suffix = archive_suffix(archive.name)
    if suffix is None:
        raise ValueError(f"不支持的压缩包格式：{archive}")
    if max_entries is not None and max_entries <= 0:
        raise ValueError("压缩包文件数量上限必须大于 0")
    if max_unpacked_bytes is not None and max_unpacked_bytes <= 0:
        raise ValueError("压缩包解压大小上限必须大于 0")

    extracted = archive.with_name(archive.name[: -len(suffix)] or "extracted")
    extracted.mkdir()

    try:
        if suffix in {".zip", ".skill"}:
            with zipfile.ZipFile(archive) as package:
                infos = package.infolist()
                for info in infos:
                    kind = stat.S_IFMT(info.external_attr >> 16)
                    allowed = {0, stat.S_IFDIR if info.is_dir() else stat.S_IFREG}
                    if kind not in allowed:
                        raise ValueError(f"压缩包包含链接或特殊文件：{info.filename}")
                _check_members(
                    ((info.filename, info.is_dir(), info.file_size) for info in infos),
                    max_entries,
                    max_unpacked_bytes,
                )
                package.extractall(extracted)
        elif suffix == ".7z":
            with py7zr.SevenZipFile(archive, max_extract_size=max_unpacked_bytes) as package:
                for member in package.files:
                    if member.is_junction or member.is_socket:
                        raise ValueError(f"压缩包包含链接或特殊文件：{member.filename}")
                infos = package.list()
                for info in infos:
                    if info.is_symlink or not (info.is_file or info.is_directory):
                        raise ValueError(f"压缩包包含链接或特殊文件：{info.filename}")
                _check_members(
                    ((info.filename, info.is_directory, info.uncompressed) for info in infos),
                    max_entries,
                    max_unpacked_bytes,
                )
                package.extractall(path=extracted)
        else:
            with tarfile.open(archive, "r:*") as package:
                infos = package.getmembers()
                for info in infos:
                    if not (info.isfile() or info.isdir()):
                        raise ValueError(f"压缩包包含链接或特殊文件：{info.name}")
                _check_members(
                    ((info.name, info.isdir(), info.size) for info in infos),
                    max_entries,
                    max_unpacked_bytes,
                )
                package.extractall(path=extracted, filter="data")
    except BaseException:
        shutil.rmtree(extracted)
        raise

    return extracted


# 压缩文件或目录
def compress_archive(file_path: str | Path, archive_format: str) -> Path:
    original = Path(file_path)
    if original.is_symlink() or original.is_junction():
        raise ValueError(f"待压缩路径不能是链接：{original}")
    source = original.resolve()
    if not source.is_file() and not source.is_dir():
        raise FileNotFoundError(f"待压缩路径不存在：{source}")
    if source.is_dir():
        for item in source.rglob("*"):
            if item.is_symlink() or item.is_junction():
                raise ValueError(f"待压缩目录包含链接：{item}")

    suffix = "." + archive_format.strip().lower().lstrip(".")
    tar_modes = {
        ".tar": "x",
        ".tar.gz": "x:gz",
        ".tgz": "x:gz",
        ".tar.bz2": "x:bz2",
        ".tbz2": "x:bz2",
        ".tar.xz": "x:xz",
        ".txz": "x:xz",
    }
    if suffix not in {".zip", ".skill", ".7z", *tar_modes}:
        raise ValueError(f"不支持的压缩格式：{archive_format}")

    compressed = source.with_name(source.name + suffix)
    if compressed.exists() or compressed.is_symlink() or compressed.is_junction():
        raise FileExistsError(f"压缩包已存在：{compressed}")

    created = False
    try:
        if suffix in {".zip", ".skill"}:
            with zipfile.ZipFile(compressed, "x", compression=zipfile.ZIP_DEFLATED) as package:
                created = True
                package.write(source, arcname=source.name)
                if source.is_dir():
                    for item in source.rglob("*"):
                        package.write(item, arcname=item.relative_to(source.parent))
        elif suffix == ".7z":
            with py7zr.SevenZipFile(compressed, "x") as package:
                created = True
                if source.is_dir():
                    package.writeall(source, arcname=source.name)
                else:
                    package.write(source, arcname=source.name)
        else:
            with tarfile.open(compressed, tar_modes[suffix]) as package:
                created = True
                package.add(source, arcname=source.name)
    except BaseException:
        if created:
            compressed.unlink(missing_ok=True)
        raise

    return compressed
