# 后端开发规则

## 常用命令
- 依赖：`uv sync` / `uv add <包>` / `uv lock`，不用 pip
- 开发启动：`make run`（热重载）
- 正式启动：`make start`

## 架构约束
- `app/` 是 Web 外壳，`harness/` 是独立框架库
- 依赖只允许 `app -> harness` 单向，`harness/` 内禁止 import `app/` 和 FastAPI 的东西
- 新接口放 `app/gateway/`，在 `app/gateway/__init__.py` 导出，在 `app/main.py` 注册
- 路由统一挂在 `system.api_prefix`（默认 /api）下，`/health` 除外
- 响应统一用 `app.schemas.result.Result` 包装

## 配置系统
- `config.yaml` 是主配置文件，程序可读写，YAML 读写统一用 ruamel（round-trip 保留注释）
- 写回用合并语义：只更新请求传来的字段，未传字段保留；原子替换
- 对外接口返回模型配置不暴露 `api_key`、`base_url`

## 历史库
- SQLite 文件路径取自 `system.db_path`（默认 `data/harness.db`），`journal_mode = WAL`，外键靠每条连接 `PRAGMA foreign_keys = ON` 开启
- DDL 唯一事实源在 `harness/storage/schema.py`，语句全部幂等，启动时在 lifespan 整段执行一遍 `SCHEMA_SCRIPT`
- 不记版本号、不做迁移链（不用 `user_version`）；给已存在的表改列要自己补 DDL 或删库重建
- 建表失败直接抛出让启动失败，不静默降级成"没有历史功能"
- 写历史走同步短事务（`connect_history_db`），写失败只 `logger.warning` 不打断回复
- 读接口翻页一律 keyset 游标，不用 OFFSET 深度分页：会话按 `(created_at, id)`，轮次按 `seq`，游标参数只给一半返回 400

## 工具规范
- 工具用 `@tool("名称", args_schema=XxxArgs)` 装饰，参数类与工具同文件，类上 `ConfigDict(extra="forbid")`
- docstring 是模型唯一能看到的说明，按段写全：功能一句话、何时使用、`Args:`、`Returns:`
- docstring 原样发给模型，`Args:`/`Returns:` 不会被剥掉，只写对调用有用的信息，不写实现细节
- 参数说明以 `args_schema` 的 `Field(description=...)` 为准，docstring 的 `Args:` 不参与生成 schema，两处措辞必须一致
- 返回值用 `json.dumps(..., ensure_ascii=False)`，输出字段在 `Returns:` 中逐个列出
- 成功路径只返回纯结果字段；一切失败（路径不存在、类型不符、非文本、缺配置等）直接 `raise ValueError(中文原因，带上完整路径)`，不在工具内 catch 转成 error 字段 JSON；`ToolCallMiddleware` 会把异常转成 error ToolMessage 回传给模型并在前端显示"失败"
- docstring 的 `Returns:` 只描述成功返回，失败行为在"何时使用"段一句话说明（如"文件不存在时工具报错"），保持与实际抛异常一致
- 新增工具在 `config.yaml` 的 `tools:` 登记 `use: 模块路径:对象名` 且 `enabled: true` 才会被主代理装配
- `group: system` 为默认组，建图时直接绑定给模型；其余组是懒加载工具，`tool_search.enabled: true` 时全量注册保证可执行，但由 `DeferredToolFilterMiddleware` 从模型可见集剔除，模型要先调 `tool_search` 取回参数定义、同一轮即可调用
- 懒加载工具必须写 `aliases`，这是 `tool_search` 的主要检索入口；`tool_search.enabled: false` 时非默认组工具不参与装配
- 懒加载工具靠 `tool_search` 结果留在对话历史里才可见，本项目未接 checkpointer，跨请求不延续，同一会话新请求需重新检索
- 部署级参数（默认上限、路径白名单等）放注册项的 `settings:`，工具运行时经 `get_app_config()` 按工具名自查，settings 缺关键项直接报错，不留代码兜底默认值；此类参数不进 args、不对模型暴露硬上限

## 代码风格
- 注释用中文短语标签，一行以内，写在被注释代码上方，如 `# 加载 yaml`
- 不做第三人称介绍式注释，不解释显而易见的代码
- 文件开头一行说明文件用途，如 `# 模型工厂`
- 类型注解全开，用 `X | None` 新语法
- 请求/响应模型用 pydantic，`ConfigDict(extra="forbid")` 严格校验

## 测试
- 改完至少跑一遍：`uv run python -c "from app.main import app"` 确认能导入
- 接口改动用 TestClient 冒烟验证状态码和关键字段
