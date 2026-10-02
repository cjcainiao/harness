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

# 依赖层，只拷锁文件，改代码不触发重装
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

# 源码层，config.yaml/.env/data/logs/.venv 一律不进镜像
COPY app/ ./app/
COPY harness/ ./harness/
# 配置模板，配置版本比对要用
COPY config.example.yaml ./

# 数据目录预建，config.yaml 挂载进来要保证运行用户可写
# 顺手清掉宿主带进来的编译缓存
RUN find /app/app /app/harness -type d -name __pycache__ -prune -exec rm -rf {} + \
    && useradd --uid 10001 --create-home --shell /bin/bash app \
    && mkdir -p /app/data /app/logs \
    && chown -R app:app /app

USER app

# 实际监听地址和端口由 config.yaml 的 system.host/port 决定，容器内需配成 0.0.0.0
EXPOSE 8000

# 健康检查，/health 不在 api 前缀下
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# 正式启动，等价 make start，但不在运行时同步依赖
CMD ["python", "-m", "app.main"]
