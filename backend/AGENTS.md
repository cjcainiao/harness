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

## 代码风格
- 注释用中文短语标签，一行以内，写在被注释代码上方，如 `# 加载 yaml`
- 不做第三人称介绍式注释，不解释显而易见的代码
- 文件开头一行说明文件用途，如 `# 模型工厂`
- 类型注解全开，用 `X | None` 新语法
- 请求/响应模型用 pydantic，`ConfigDict(extra="forbid")` 严格校验

## 测试
- 改完至少跑一遍：`uv run python -c "from app.main import app"` 确认能导入
- 接口改动用 TestClient 冒烟验证状态码和关键字段
