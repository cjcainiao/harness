# 后端开发规则

## 常用命令
- 依赖：`uv sync` / `uv add <包>` / `uv lock`，不用 pip
- 开发启动：`make run`（热重载）
- 正式启动：`make start`

## 架构约束
- `app/` 是 Web 外壳，`harness/` 是独立框架库
- 依赖只允许 `app -> harness` 单向，`harness/` 内禁止 import `app/` 和 FastAPI 的东西
- `harness/` 各包的 `__init__.py` 默认只写一行包说明；只聚合同名类的包（如 `middlewares`）可以导出，但不得 re-export 会拉起整条依赖链的模块（`runtime/__init__.py` 导 `stream` 就绕回 `storage.db` 成了环）
- 新接口放 `app/gateway/`，在 `app/gateway/__init__.py` 导出，在 `app/main.py` 注册
- 路由统一挂在 `system.api_prefix`（默认 /api）下，`/health` 除外
- 响应统一用 `app.schemas.result.Result` 包装

## 配置系统
- `config.yaml` 是主配置文件，程序可读写，YAML 读写统一用 ruamel（round-trip 保留注释）
- 写回用合并语义：只更新请求传来的字段，未传字段保留；原子替换
- 对外接口返回模型配置不暴露 `api_key`、`base_url`
- 可调参数只认 `config.yaml` 一个出处，模块里不留同名的硬编码常量（如锁等待时长走 `system.db_busy_timeout_ms`，不写 `BUSY_TIMEOUT_MS`）
- 新增配置键要同步补 `config.example.yaml`；`Field(description=...)` 与 YAML 行内注释同一句话，注释列与相邻行对齐；`config_version` 不因加键 bump
- `config.yaml` 不入版本控制且含真实密钥，核对只按行读指定键，不整文件 diff、不打印密钥行

## 历史库
- SQLite 文件路径取自 `system.db_path`（默认 `data/harness.db`），`journal_mode = WAL`，每条连接由 `session_pragmas()` 统一开启 `foreign_keys` 与 `busy_timeout`
- 库文件的相对路径统一由 `harness/runtime/db_path.py:resolve_db_path` 按后端项目根展开，历史库和检查点库共用它，不受启动目录影响
- DDL 唯一事实源在 `harness/storage/schema.py`，语句全部幂等，启动时在 lifespan 整段执行一遍 `SCHEMA_SCRIPT`
- 不记版本号、不做迁移链（不用 `user_version`）；给已存在的表改列要自己补 DDL 或删库重建
- 建表失败直接抛出让启动失败，不静默降级成"没有历史功能"
- 写历史走同步短事务（`connect_history_db`），写失败只 `logger.warning` 不打断回复
- 读接口翻页一律 keyset 游标，不用 OFFSET 深度分页：会话按 `(created_at, id)`，轮次按 `seq`，游标参数只给一半返回 400
- 检查点存 `memory.db_path`（默认 `data/checkpoints.db`），表由 `AsyncSqliteSaver.setup()` 自建自管，不进 `schema.py` 也不进 `SCHEMA_SCRIPT`，两条 DDL 互不相关
- 检查点只支持单进程写入（`aiosqlite` 长连接），多 worker 部署要换 postgres 版 saver
- 节点内 `get_config()` 的 `checkpoint_ns` 是 `model:task_id`，读主代理历史要只传 `thread_id`；saver 的同步 `get_tuple` 在它自己的事件循环里会报错，只在异步包装里读

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
- 懒加载工具靠 `tool_search` 结果留在对话历史里才可见，接了检查点后同一 `thread_id` 的历史跨请求延续，换会话要重新检索
- 部署级参数（默认上限、路径白名单等）放注册项的 `settings:`，工具运行时经 `get_app_config()` 按工具名自查，settings 缺关键项直接报错，不留代码兜底默认值；此类参数不进 args、不对模型暴露硬上限

## 技能规范
- 技能内容与加载代码分开：技能包在 `backend/skills/`，扫描与名单渲染在 `harness/skills/`
- 技能根目录取自 `skills.dir`，相对路径按后端项目根解析；`skills.enabled: false` 时不扫描、不注入提示词
- 根目录下按 `skills.categories` 分分类目录，`custom` 放项目自己写的技能（入版本控制），`public` 放第三方装进来的（`.gitignore` 掉），靠前的分类优先
- 一个技能一个目录，目录内必须有 `skills.file`（默认 `SKILL.md`）；放进目录即启用，目录名加 `.` 前缀即停用，不留第二份启用状态
- frontmatter 只写 `name` 和 `description`：`name` 必须等于所在目录名，字符集取自 `skills.name_pattern`（默认小写字母、数字与连字符）；`description` 说清做什么与何时使用，上限取自 `skills.description_limit`（默认 1024 字）
- 三个可选子目录按用途固定：`scripts/` 放可执行代码，`references/` 放文档资料，`assets/` 放模板与静态资源；代码文件不进 `assets/`
- `SKILL.md` 正文只写判断和执行顺序，细节一律推到 `references/`，建议 60 行以内
- 渐进披露：提示词只注入技能名、描述和主文件绝对路径，正文由模型自己用 `read_file` 取，不预注入
- 进提示词的技能条数受 `skills.max_in_prompt` 限制，先按分类再按名字排序，超出截断并告警
- 不为技能新增取用工具，通道就是 `read_file`
- 每次建图重扫技能目录，不做缓存；改完 `SKILL.md` 下一轮生效
- 技能名重复时保留排序靠前的，后者告警跳过，不静默覆盖
- 符号链接目录不跟随；根目录不存在告警后按空名单处理，缺主文件、缺 `name` 或 `description`、字符集不合规等技能包逐个告警跳过，建图不因技能失败
- 写进提示词的技能路径一律绝对路径，分隔符用 `/`
- 现有工具里没有执行命令的，`scripts/` 由开发侧运行，技能正文不得声称模型能运行它
- 技能包结构自检：`uv run python skills/custom/<技能名>/scripts/check_skill.py`，退出码非 0 按提示改

## 镜像构建
- `backend/Dockerfile` 的构建上下文就是 `backend/` 目录，COPY 清单固定为 `app/`、`harness/`、`pyproject.toml`、`uv.lock`、`.python-version`、`config.yaml`、`.env`，新增要进镜像的文件得同步这一处
- 依赖只按锁文件装：`uv sync --frozen --no-dev --no-install-project`，`harness` 本身不是可安装包
- `config.yaml` 与 `.env` 烘进镜像，容器内 `system.host` 必须是 `0.0.0.0`，否则端口映射打不通；密钥随镜像层分发，镜像要外发前先换成运行期注入
- 监听端口取自 `config.yaml`，`EXPOSE` 和 `HEALTHCHECK` 里的 8000 是写死的，改端口要同步这两处
- 启动用 `python -m app.main`，不走 `uv run` 所以不触发依赖同步；`.env` 靠 `harness/config/app_config.py` 自己 `load_dotenv`

## 代码风格
- 注释用中文短语标签，一行以内，写在被注释代码上方，如 `# 加载 yaml`
- 不做第三人称介绍式注释，不解释显而易见的代码
- 注释只写当前这段代码：不描述调用方或别的模块会怎么反应，不复述签名、参数名、类型注解和返回值
- `except` 分支的注释只交代为什么这么放行，如 `# 调试读库失败不打断模型调用`
- 配置类字段不写注释，说明只放 `Field(description=...)`；工具 `args_schema` 字段写一行名词短语，如 `# 待统计的文本`，取值优先级留在 description
- DDL 与 YAML 逐字段一行注释
- 未实现的骨架函数照样按短语标签注释
- 文件开头一行说明文件用途，如 `# 模型工厂`
- 类型注解全开，用 `X | None` 新语法
- 请求/响应模型用 pydantic，`ConfigDict(extra="forbid")` 严格校验

## 测试
- 改完至少跑一遍：`uv run python -c "from app.main import app"` 确认能导入
- 接口改动用 TestClient 冒烟验证状态码和关键字段
