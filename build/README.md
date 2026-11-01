# Harness 构建与部署

`build` 中的脚本生成 `output` 部署目录。每次运行脚本都会清空并重新生成 `output`，不要在其中直接保存需要长期保留的文件。

## 准备

- 前端已安装依赖；尚未安装时，在 `frontend` 目录运行 `npm ci`。
- 后端已有 `backend/.env`，其中需配置 `DEEPSEEK_API_KEY` 等服务密钥。
- 后端配置取 `backend/config.yaml`；该文件不入库，缺失时脚本自动改用 `backend/config.example.yaml`，请在打包前确认配置内容与密钥引用正确。
- 部署服务器已安装 Docker 和 Docker Compose。

## 本地打包

在项目根目录运行：

```powershell
# Windows
.\build\build.bat
```

```bash
# Linux / macOS
bash build/build.sh
```

脚本依次复制后端运行文件、构建前端，并生成以下部署目录：

```text
build/output/
├─ backend/             后端代码、配置、环境变量和依赖锁文件
│  ├─ config.yaml       直接运行时的默认配置
│  └─ config/           容器挂载用的配置目录
├─ frontend/            前端静态文件
├─ Dockerfile           后端镜像构建文件
├─ docker-compose.yaml  双容器编排
├─ nginx.conf           前端路由与接口转发
└─ README.md            本说明
```

## 服务器部署

1. 将整个 `build/output` 目录复制到服务器。
2. 在服务器的 `output` 目录启动：

```bash
docker compose up -d --build
```

前端地址为 `http://服务器地址/`，后端健康检查为 `http://服务器地址:8000/health`。宿主机端口分别映射到前端容器的 `80` 和后端容器的 `8000`；Nginx 将前端的 `/api` 请求转发到同一 Compose 网络中的 `backend:8000`。

## 挂载与配置

| 服务 | 挂载 | 用途 |
| --- | --- | --- |
| 后端 | `backend_data` → `/app/data` | 持久保存 SQLite 数据库与会话工作空间 |
| 后端 | `backend_logs` → `/app/logs` | 持久保存日志 |
| 后端 | `./backend/config` → `/app/config` | 运行期配置文件 |
| 后端 | `backend_skills` → `/app/skills/public` | 第三方技能安装目录 |
| 前端 | `./frontend` → `/usr/share/nginx/html`（只读） | 提供打包后的页面 |
| 前端 | `./nginx.conf` → `/etc/nginx/conf.d/default.conf`（只读） | 配置前端路由和接口转发 |

后端 `.env` 在构建镜像时复制到镜像的 `/app/.env`，运行容器时无需再传入。修改 `.env` 后需要重新构建镜像。

配置按目录挂载，不能用单文件挂载：配置页保存时用临时文件加 `os.replace` 做原子替换，单文件挂载会让替换跨设备失败。`config.yaml` 中的监听地址需与容器内的 `0.0.0.0:8000` 对应，仓库里的 `127.0.0.1` 要在部署前改掉。修改挂载的配置后重启后端容器。

## 常用命令

在服务器的 `output` 目录执行：

```bash
docker compose ps                 # 查看容器状态
docker compose logs -f            # 查看前后端日志
docker compose up -d --build      # 重新构建并启动
docker compose down               # 停止容器，保留数据库和日志卷
```
