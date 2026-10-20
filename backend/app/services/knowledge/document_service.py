# 知识库文档业务

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import sqlite3
from contextlib import suppress
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from harness.config.app_config import get_app_config
from harness.rag.document.pipeline import index_document
from harness.rag.document.repository import (
    create_document,
    delete_base,
    delete_document,
    get_base,
    get_document,
    pending_documents,
    set_document_status,
)
from harness.rag.store import document_path, rag_files_dir


ALLOWED_SUFFIXES = frozenset({".md", ".markdown", ".txt", ".html", ".htm", ".pdf", ".docx"})
_running_jobs: dict[str, asyncio.Task[None]] = {}


def _valid_name(filename: str | None) -> tuple[str, str]:
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    suffix = Path(name).suffix.lower()
    if not name or len(name) > 255 or any(ord(char) < 32 for char in name) or suffix not in ALLOWED_SUFFIXES:
        raise ValueError("知识库文档文件名或格式无效")
    return name, suffix


def save_document(base_id: str, filename: str | None, source: BinaryIO) -> dict:
    name, suffix = _valid_name(filename)
    if get_base(base_id) is None:
        raise LookupError("知识库不存在")
    files_dir = rag_files_dir()
    files_dir.mkdir(parents=True, exist_ok=True)
    temporary = files_dir / f".upload-{uuid4().hex}.tmp"
    size = 0
    digest = hashlib.sha256()
    try:
        with temporary.open("xb") as target:
            while part := source.read(1024 * 1024):
                size += len(part)
                if size > get_app_config().rag.upload_max_bytes:
                    raise ValueError("知识库文档超过大小限制")
                digest.update(part)
                target.write(part)
        if size == 0:
            raise ValueError("知识库文档不能为空")
        with temporary.open("rb") as stream:
            header = stream.read(8)
        if suffix == ".pdf" and not header.startswith(b"%PDF-"):
            raise ValueError("PDF 文件内容无效")
        if suffix == ".docx" and not header.startswith(b"PK"):
            raise ValueError("DOCX 文件内容无效")
        try:
            item = create_document(base_id, name, digest.hexdigest(), size, suffix)
        except sqlite3.IntegrityError as error:
            raise ValueError("该知识库已存在相同内容的文档") from error
        target = document_path(base_id, item["id"])
        try:
            target.parent.mkdir(parents=True, exist_ok=False)
            os.replace(temporary, target)
        except OSError as error:
            set_document_status(item["id"], "failed", "原文件保存失败")
            raise ValueError("原文件保存失败") from error
        return item
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)


def remove_document(document_id: str) -> dict:
    item = delete_document(document_id)
    if item is None:
        raise LookupError("文档不存在")
    directory = document_path(item["base_id"], document_id).parent
    if directory.is_dir() and not directory.is_symlink():
        shutil.rmtree(directory)
    return item


def remove_base(base_id: str) -> None:
    if not delete_base(base_id):
        raise LookupError("知识库不存在")
    directory = rag_files_dir() / base_id
    if directory.is_dir() and not directory.is_symlink():
        shutil.rmtree(directory)


def schedule_document(document_id: str) -> None:
    if document_id in _running_jobs:
        return
    job = asyncio.create_task(index_document(document_id))
    _running_jobs[document_id] = job

    def finish(finished: asyncio.Task[None]) -> None:
        if _running_jobs.get(document_id) is finished:
            _running_jobs.pop(document_id, None)

    job.add_done_callback(finish)


async def recover_documents() -> None:
    for document_id in await asyncio.to_thread(pending_documents):
        schedule_document(document_id)


async def shutdown_documents() -> None:
    for job in tuple(_running_jobs.values()):
        job.cancel()
    if _running_jobs:
        await asyncio.gather(*_running_jobs.values(), return_exceptions=True)
