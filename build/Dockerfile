# 后端镜像构建文件
FROM python:3.12-slim-bookworm AS dependencies

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# 依赖单独成层
RUN pip install --no-cache-dir uv==0.11.16
COPY pyproject.toml uv.lock .python-version /app/
# 只装第三方依赖，harness 不是可安装包
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim-bookworm

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HARNESS_CONFIG_PATH=/app/config/config.yaml

WORKDIR /app

COPY --from=dependencies /app/.venv /app/.venv
COPY app /app/app
COPY harness /app/harness
COPY skills /app/skills
COPY config /app/config
COPY .env /app/.env

# 数据、日志、配置与技能目录交给应用用户
RUN groupadd --system harness \
    && useradd --system --gid harness --home-dir /app --no-create-home harness \
    && mkdir -p /app/data /app/logs /app/config /app/skills/public \
    && chown -R harness:harness /app/data /app/logs /app/config /app/skills/public /app/.env \
    && chmod 600 /app/.env

USER harness
EXPOSE 8000

CMD ["python", "-m", "app.core.main"]
