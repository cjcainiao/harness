# 统一响应结果

from typing import Self

from pydantic import BaseModel, Field


class Result[T](BaseModel):
    code: int = Field(default=200, ge=0, description="响应编码")
    message: str = Field(default="成功", description="响应消息")
    data: T | None = Field(default=None, description="响应数据")

    # 构建成功结果
    @classmethod
    def success(
        cls,
        data: T | None = None,
        message: str = "成功",
    ) -> Self:
        return cls(
            code=200,
            message=message,
            data=data,
        )

    # 构建错误结果
    @classmethod
    def error(
        cls,
        code: int,
        message: str,
        data: T | None = None,
    ) -> Self:
        return cls(
            code=code,
            message=message,
            data=data,
        )
