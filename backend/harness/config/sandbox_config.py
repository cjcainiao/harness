# 沙箱配置

from pydantic import BaseModel, ConfigDict, Field


# 沙箱配置类
class SandboxConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    use: str = Field(
        default="harness.sandbox.local.local_sandbox_provider:LocalSandboxProvider",
        min_length=1,
        description="沙箱提供者类路径，格式为 module:Class",
    )
