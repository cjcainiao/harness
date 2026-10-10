---
name: add-local-tool
description: 在 Harness 后端给主代理新增一个可真实调用的本地工具时使用。覆盖工具文件放哪个主题族、参数模型与 docstring 分段、config.yaml 的 tools 登记、system 组与懒加载组的可见性差别、部署级参数的读取方式，以及改完的导入与调用验收。用户提出"加个工具""接入某个能力""让模型能查/能改某样东西"，或要改动 harness/tools/ 与配置里的 tools 段时，都按本流程走。
---

# 新增本地工具

给主代理加一个它能真正调用到的工具。以下路径均以 `backend/` 为工作目录。规则细节以 `AGENTS.md` 的「工具规范」为准，这里是执行顺序。

## 动手前先定两件事

1. **主题族**：工具文件按主题族归置，现有 `system`（时间、文件操作）、`text`（字数统计）。新能力优先放进已有主题族的现有模块，一族多工具，不做一工具一文件。
2. **可见性组**：`group: system` 建图时直接绑定给模型，写完就能调；其余组是懒加载，靠 `tool_search` 先取回参数定义才能调，且**必须写 `aliases`**（这是检索的主要入口）。

拿不准就选已有主题族 + `group: system`，代价最小。

## 执行顺序

1. 在 `harness/tools/<组>/<模块>.py` 里写参数类和工具，同一个文件、同属一个主题。
2. 参数类继承 `BaseModel`，带上 `ConfigDict(extra="forbid", str_strip_whitespace=True)`；每个字段一行名词短语注释，说明只写进 `Field(description=...)`。
3. 用 `@tool("工具名", args_schema=XxxArgs)` 装饰，docstring 四段写全：功能一句话、何时使用（失败行为在这段说一句）、`Args:`、`Returns:`。docstring 原样发给模型，`Args:`/`Returns:` 不会被剥掉，只写对调用有用的信息，不写实现细节。
4. 返回值用 `json.dumps(..., ensure_ascii=False)`，成功路径只放结果字段，字段在 `Returns:` 里逐个列出。
5. 一切失败（路径不存在、类型不符、缺配置等）直接 `raise ValueError(中文原因，带上完整路径)`，不在工具内 catch 转成 error 字段——中间件会把异常翻成 error 结果回传给模型。`Returns:` 只描述成功返回。
6. 部署级参数（默认上限、路径白名单之类）放注册项的 `settings:`，运行时用 `get_tool_settings("工具名")` 自查；settings 缺关键项就直接报错，不留代码兜底默认值，这类参数也不进 args、不对模型暴露硬上限。
7. 在 `config.yaml` 和 `config.example.yaml` 的 `tools:` 各登记一条完整条目，两份字段一致（config.yaml 不入版本控制，但本机运行靠它）。
8. 自查注释口径（短语标签、一行以内、不解释显而易见的代码、文件开头一行说明用途），再走验收。

## 随包文件

- `skills/custom/add-local-tool/references/config-registration.md`：完整 YAML 条目写法、参数类与 docstring 模板、验收命令、常见漏项。要用文件读取工具读它，不要凭本文件的概述猜细节。
- `skills/custom/add-local-tool/assets/tool_registration.yaml`：`tools:` 段的登记条目模板，替换占位值后粘进两份配置。
- `skills/custom/add-local-tool/scripts/check_skill.py`：技能包结构自检。本期没有可执行命令的工具，模型只能读它的源码，不要承诺运行它；跑由开发侧执行。

## 验收（一条都不能省）

- 技能本身有改动：由开发侧运行 `uv run python skills/custom/add-local-tool/scripts/check_skill.py`，退出码 0
- `uv run python -c "from app.main import app"` 通过
- 懒加载组的工具：确认它出现在 `tool_search` 的目录里（`build_registry()` 返回里有它）
- 重启后端进程后，用一句明确匹配该能力的提问确认工具真被调用并有返回结果，而不是只在文字里声称
- 加配置键不 bump `config_version`
