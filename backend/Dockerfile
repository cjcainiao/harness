# docker 构建文件

FROM python:3.12-slim

# uv 只取二进制，不装进 Python 环境
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

# 常用网络工具，构建镜像时可用（调试使用）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        wget \
        iputils-ping \
        iproute2 \
        netcat-openbsd \
        dnsutils \
        procps \
        tzdata \
        vim-tiny \
        less \
    && rm -rf /var/lib/apt/lists/*

# 时区与 Python 行为，日志按本地时间输出
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:${PATH}

WORKDIR /app

# 主程序包
COPY app/ ./app/
# 框架包
COPY harness/ ./harness/
# 技能包
COPY skills/ ./skills/
# 依赖清单与 Python 版本
COPY pyproject.toml uv.lock .python-version ./
# 运行配置
COPY config.yaml ./
# 密钥取值来源
COPY .env ./

# 按锁文件装依赖，不含 dev 组，项目本身不是可安装包
RUN uv sync --frozen --no-dev --no-install-project --no-cache

# 清编译缓存，建数据与日志目录，整棵树交给运行用户
RUN find /app/app /app/harness -type d -name __pycache__ -prune -exec rm -rf {} + \
    && useradd --uid 10001 --create-home --shell /bin/bash app \
    && mkdir -p /app/data /app/logs \
    && chown -R app:app /app

USER app

# 监听地址和端口取自镜像内 config.yaml 的 system.host/port，必须是 0.0.0.0
EXPOSE 8000

# 健康检查，/health 不在 api 前缀下
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# 正式启动，等价 make start，但不在运行时同步依赖
CMD ["python", "-m", "app.main"]
