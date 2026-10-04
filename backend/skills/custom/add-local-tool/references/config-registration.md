# 工具登记与模板细节

`SKILL.md` 执行顺序对应的模板都在这一份。抄现成的参照文件：`backend/harness/tools/system/file_operations.py`（一族四工具、带 settings）、`backend/harness/tools/text/word_count.py`（懒加载组）。

## 参数类与工具骨架

要空骨架直接照下面这份改；要往配置里登记的条目模板在 `../assets/tool_registration.yaml`，那份文件自身可解析，取 `tools:` 下那条粘进列表末尾。

```python
# 目录统计工具

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from harness.tools.tool_settings import get_tool_settings


# 统计目录参数
class CountFilesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 要统计的目录路径
    path: str = Field(min_length=1, description="本地目录路径，绝对或相对工作目录")

    # 返回条目数上限，未提供时用配置 settings 的默认值
    max_entries: int | None = Field(
        default=None,
        gt=0,
        description="统计时最多遍历的条目数，超出即停止；未提供时使用工具配置 default_max_entries",
    )


# 统计目录下的文件数量
@tool("count_files", args_schema=CountFilesArgs)
def count_files(path: str, max_entries: int | None = None) -> str:
    """统计目录下指定类型的文件数量。

    需要清点某个目录里有多少个某类文件时使用，只统计第一层不递归。
    路径不存在或不是目录时工具报错，错误原因随工具结果返回。

    Args:
        path: 本地目录路径，绝对或相对工作目录。
        max_entries: 统计时最多遍历的条目数，超出即停止；未提供时使用工具配置 default_max_entries。

    Returns:
        JSON 对象字符串，含三个字段：
        - path: 实际统计的绝对路径
        - total: 命中的文件数量
        - truncated: 是否因超出 max_entries 提前停止
    """
    settings = get_tool_settings("count_files")
    if "default_max_entries" not in settings:
        raise ValueError("count_files 未配置 default_max_entries")
    limit = max_entries or int(settings["default_max_entries"])

    target = Path(path).expanduser()
    if not target.is_absolute():
        target = Path.cwd() / target
    target = target.resolve()

    if not target.is_dir():
        raise ValueError(f"路径不存在或不是目录：{target}")

    total = 0
    scanned = 0
    for item in target.iterdir():
        scanned += 1
        if item.is_file():
            total += 1
        if scanned >= limit:
            break

    return json.dumps(
        {"path": str(target), "total": total, "truncated": scanned >= limit},
        ensure_ascii=False,
    )
```

要点：文件开头一行说明文件用途；参数类与工具同文件；类上 `extra="forbid"`；字段注释是一行名词短语、说明只在 `Field(description=...)`；`settings` 缺关键项直接报错，不留兜底默认值。

## docstring 四段口径

- 功能一句话：说清"对什么东西做什么"。
- 何时使用：什么场景该调它，附一句边界（只第一层不递归、仅文本文件），失败行为也在这段说一句，保持和抛异常一致。
- `Args:`：逐参数说明，措辞与 `args_schema` 的 `Field(description=...)` 必须同一句话——两处不一致时模型看到的和用户填的会对不上。
- `Returns:`：只描述成功返回，逐个列出输出字段。不写失败分支。

不要写实现细节、不要写跨层契约、不要写调用方会怎么反应。

## YAML 登记：默认组

```yaml
  - name: count_files # 工具名称
    group: system # 所属工具组
    use: harness.tools.system.file_operations:count_files # 工具实现
    enabled: true # 是否启用
    aliases: [统计文件数, 清点目录] # 查找别名
    settings: {
      default_max_entries: 200 # 最多遍历条目数
    } # 工具额外配置
```

`group: system` 的工具建图时直接绑定给模型，`aliases` 用不上但仍登记，保持条目形状一致。

## YAML 登记：懒加载组

```yaml
  - name: count_files # 工具名称
    group: text # 所属工具组
    use: harness.tools.text.count_files:count_files # 工具实现
    enabled: true # 是否启用
    aliases: [统计文件数, 清点目录, 文件计数] # 查找别名
```

- `aliases` 必填，`tool_search` 是整段包含匹配、不是语义搜索：给 2-4 字的核心能力词，多个写法都列上。
- 懒加载只在 `tool_search.enabled: true` 时参与装配；关掉时非默认组工具不建图、模型也看不到。
- 新开一个主题族时：建 `backend/harness/tools/<组>/__init__.py`（一行包说明），并在 `config.example.yaml` 与 `config.yaml` 的 `tool_groups:` 补一行分组名，两处 group 值要和它对上。

## 改 config.yaml 的注意

`backend/config.yaml` 不入版本控制且含真实密钥。核对只按行读需要的那个键，不要整文件 diff、不要打印密钥行；往 `tools:` 追加条目时按缩进照现有条目抄，别动别的段。

## 验收命令

```bash
cd backend
uv run python -c "from app.main import app; print('import ok')"

# 懒加载组：确认进了目录
uv run python -c "from harness.tools.tool_search import build_registry, registry_entries; build_registry(); print([e.name for e in registry_entries()])"

# 默认组：确认直接绑定得到
uv run python -c "from harness.tools.loader import load_default_tools; print([t.name for t in load_default_tools()])"
```

接口或装配有改动时，再用 TestClient 冒烟一次状态码和关键字段。后端进程不热重载，改完要重启才生效。

## 常见漏项

- 忘了在 `config.yaml` 登记，只改了 example：本机跑不到，且 example 与真实配置不一致
- `Args:` 和 `Field(description=...)` 措辞不一致
- 用 `settings:` 之外的硬编码常量当默认上限
- 在工具里把异常 catch 成 `{"error": ...}` 返回，破坏"失败一律上抛"的既定语义
- 懒加载组没写 `aliases`，模型检索不到，等于工具不存在
- 成功返回里混进 `code`/`message` 这类包装字段：工具返回给模型的是纯结果，`Result` 包装只在 HTTP 层
- 同主题的新能力另起一个单工具文件，让一个模块里只住一个工具
