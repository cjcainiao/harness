# 会话状态字段

from typing import Any, NotRequired

from langchain.agents import AgentState


# 主代理会话状态
class ThreadState(AgentState):
    # 本轮上传的文件
    uploaded_files: NotRequired[list[dict[str, Any]] | None]
