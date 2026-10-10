# 会话状态字段

from typing import Annotated, NotRequired, TypedDict

from langchain.agents import AgentState


# 已开放工具记录
class PromotedTools(TypedDict):
    catalog_hash: str
    names: list[str]


# 已上传附件信息
class UploadedFileInfo(TypedDict):
    file_id: str
    thread_id: str
    name: str
    size: int
    mime_type: str
    created_at: str
    preview_url: str


# 已查看图片信息
class ViewedImageData(TypedDict):
    mime_type: str
    size: int
    actual_path: str
    sha256: str


# 已开放工具合并
def merge_promoted(existing: PromotedTools | None, new: PromotedTools | None) -> PromotedTools | None:
    if not new:
        return existing
    if existing is None or existing["catalog_hash"] != new["catalog_hash"]:
        return {"catalog_hash": new["catalog_hash"], "names": list(dict.fromkeys(new["names"]))}
    return {
        "catalog_hash": existing["catalog_hash"],
        "names": list(dict.fromkeys([*existing["names"], *new["names"]])),
    }


# 已查看图片合并
def merge_viewed_images(
    existing: dict[str, ViewedImageData] | None,
    new: dict[str, ViewedImageData] | None,
) -> dict[str, ViewedImageData]:
    if new is None:
        return existing or {}
    if not new:
        return {}
    return {**(existing or {}), **new}


# 主代理会话状态
class ThreadState(AgentState):
    # 已开放工具
    promoted: Annotated[PromotedTools | None, merge_promoted]

    # 本轮上传的附件信息
    uploaded_files: NotRequired[list[UploadedFileInfo]]

    # 已查看图片信息，键为图片路径
    viewed_images: Annotated[dict[str, ViewedImageData], merge_viewed_images]

    # 会话工作空间路径
    workspace_path: NotRequired[str | None]
