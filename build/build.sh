#!/usr/bin/env bash
# 部署打包脚本
set -Eeuo pipefail

# 按脚本位置定位项目目录
BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd "$BUILD_DIR/.." && pwd -P)"
BACKEND_SOURCE="$PROJECT_DIR/backend"
FRONTEND_SOURCE="$PROJECT_DIR/frontend"
OUTPUT_DIR="$BUILD_DIR/output"
BACKEND_TARGET="$OUTPUT_DIR/backend"
FRONTEND_TARGET="$OUTPUT_DIR/frontend"

# 结束前停留几秒，--no-pause 关闭
WAIT_AT_END=1
if [[ "${1:-}" == "--no-pause" ]]; then
    WAIT_AT_END=0
fi
finish() {
    status=$?
    trap - EXIT
    if (( status != 0 )); then
        printf 'Build failed.\n' >&2
    fi
    if (( WAIT_AT_END )); then
        sleep 5
    fi
    exit "$status"
}
trap finish EXIT

# 后端入口与运行文件校验
if [[ ! -f "$BACKEND_SOURCE/app/main.py" ]]; then
    printf 'Backend source was not found: %s\n' "$BACKEND_SOURCE" >&2
    exit 1
fi
for file in pyproject.toml uv.lock .python-version config.yaml .env; do
    if [[ ! -f "$BACKEND_SOURCE/$file" ]]; then
        printf 'Required backend file is missing: %s\n' "$file" >&2
        exit 1
    fi
done
for dir in app harness skills; do
    if [[ ! -d "$BACKEND_SOURCE/$dir" ]]; then
        printf 'Required backend directory is missing: %s\n' "$dir" >&2
        exit 1
    fi
done
if [[ ! -f "$FRONTEND_SOURCE/package.json" ]]; then
    printf 'Frontend source was not found: %s\n' "$FRONTEND_SOURCE" >&2
    exit 1
fi

# 部署文件校验
for file in Dockerfile docker-compose.yaml nginx.conf README.md; do
    if [[ ! -f "$BUILD_DIR/$file" ]]; then
        printf 'Required deployment file is missing: %s\n' "$file" >&2
        exit 1
    fi
done
command -v tar >/dev/null
command -v npm >/dev/null

# 校验产物路径后清空，链接一律拒绝
if [[ "$BUILD_DIR" != "$PROJECT_DIR/build" || "$OUTPUT_DIR" != "$BUILD_DIR/output" ]]; then
    printf 'Unsafe build output path.\n' >&2
    exit 1
fi
if [[ -L "$OUTPUT_DIR" ]]; then
    printf 'Build output is a link: %s\n' "$OUTPUT_DIR" >&2
    exit 1
fi
if [[ -e "$OUTPUT_DIR" ]]; then
    if [[ ! -d "$OUTPUT_DIR" ]] || [[ -n "$(find "$OUTPUT_DIR" -type l -print -quit)" ]]; then
        printf 'Build output is not a regular directory: %s\n' "$OUTPUT_DIR" >&2
        exit 1
    fi
    rm -rf -- "$OUTPUT_DIR"
fi

mkdir -p "$BACKEND_TARGET"

# 复制后端代码，排除缓存与本地数据
for dir in app harness skills; do
    tar -C "$BACKEND_SOURCE" \
        --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' -cf - "$dir" \
        | tar -C "$BACKEND_TARGET" -xf -
done
for file in pyproject.toml uv.lock .python-version .env; do
    cp -p "$BACKEND_SOURCE/$file" "$BACKEND_TARGET/$file"
done

# 配置放目录里，配置页保存要能原子替换
mkdir -p "$BACKEND_TARGET/config"
cp -p "$BACKEND_SOURCE/config.yaml" "$BACKEND_TARGET/config/config.yaml"

# 技能运行时安装，保留挂载点
mkdir -p "$BACKEND_TARGET/skills/public"
: > "$BACKEND_TARGET/skills/public/.gitkeep"
printf 'Backend files copied: %s\n' "$BACKEND_TARGET"

# 构建前端，只取生产产物
(cd "$FRONTEND_SOURCE" && npm run build)
if [[ ! -f "$FRONTEND_SOURCE/dist/index.html" ]]; then
    printf 'Frontend output was not found: %s\n' "$FRONTEND_SOURCE/dist" >&2
    exit 1
fi
mkdir -p "$FRONTEND_TARGET"
cp -R "$FRONTEND_SOURCE/dist/." "$FRONTEND_TARGET/"
printf 'Frontend files copied: %s\n' "$FRONTEND_TARGET"

# 复制部署文件
cp -p "$BUILD_DIR/Dockerfile" "$OUTPUT_DIR/Dockerfile"
cp -p "$BUILD_DIR/docker-compose.yaml" "$OUTPUT_DIR/docker-compose.yaml"
cp -p "$BUILD_DIR/nginx.conf" "$OUTPUT_DIR/nginx.conf"
cp -p "$BUILD_DIR/README.md" "$OUTPUT_DIR/README.md"
printf 'Build completed: %s\n' "$OUTPUT_DIR"
