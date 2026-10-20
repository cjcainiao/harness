# 知识库文档解析与索引

from __future__ import annotations

import asyncio
from pathlib import Path

from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from markitdown import MarkItDown, StreamInfo

from harness.config.app_config import get_app_config
from harness.core.logger import get_logger
from harness.rag.document.repository import (
    get_document,
    replace_document_chunks,
    set_document_status,
)
from harness.rag.embedding import embed_texts, embedding_text
from harness.rag.store import document_path


logger = get_logger(__name__)


def parse_document(source: Path, name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix in {".md", ".markdown", ".txt"}:
        content = source.read_text(encoding="utf-8-sig")
    elif suffix in {".html", ".htm"}:
        content = BeautifulSoup(source.read_text(encoding="utf-8-sig"), "html.parser").get_text("\n")
    elif suffix in {".pdf", ".docx"}:
        with source.open("rb") as stream:
            result = MarkItDown().convert_stream(stream, stream_info=StreamInfo(filename=name, extension=suffix))
        content = result.markdown
    else:
        raise ValueError(f"不支持的知识库文档格式：{name}")
    if not content.strip():
        raise ValueError("文档未提取到文字")
    return content


def split_document(content: str) -> list[dict[str, str]]:
    config = get_app_config().rag
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    )
    sections: list[tuple[str, str]] = []
    heading = "正文"
    lines: list[str] = []
    for line in content.splitlines():
        if line.lstrip().startswith("# ") or line.lstrip().startswith("## ") or line.lstrip().startswith("### "):
            if lines:
                sections.append((heading, "\n".join(lines)))
                lines = []
            heading = line.lstrip("# ").strip() or "正文"
        else:
            lines.append(line)
    if lines:
        sections.append((heading, "\n".join(lines)))
    return [
        {"heading": heading, "content": part.strip()}
        for heading, text in sections
        for part in splitter.split_text(text)
        if part.strip()
    ]


async def index_document(document_id: str) -> None:
    document = await asyncio.to_thread(get_document, document_id)
    if document is None:
        return
    source = document_path(document["base_id"], document_id)
    try:
        await asyncio.to_thread(set_document_status, document_id, "parsing")
        content = await asyncio.to_thread(parse_document, source, document["name"])
        chunks = split_document(content)
        if not chunks:
            raise ValueError("文档未生成可检索片段")
        await asyncio.to_thread(set_document_status, document_id, "indexing")
        vectors = await embed_texts([
            embedding_text(document["name"], chunk["heading"], chunk["content"])
            for chunk in chunks
        ])
        await asyncio.to_thread(replace_document_chunks, document_id, chunks, vectors)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        logger.warning("知识库文档索引失败", document_id=document_id, error=str(error))
        await asyncio.to_thread(set_document_status, document_id, "failed", str(error)[:1000])
