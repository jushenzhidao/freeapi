FROM python:3.13-slim

LABEL maintainer="313303303@qq.com"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

EXPOSE 8000

# 安装 uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ADD https://releases.astral.sh/installers/uv/latest/uv-installer.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# 先复制依赖声明（利用缓存层）
COPY pyproject.toml uv.lock ./

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

# 复制项目源码（适配你的结构）
COPY app/ ./app/
COPY main.py startup.sh  ./

# 创建非 root 用户
#RUN adduser -u 5678 --disabled-password --gecos "" appuser && \
#    chown -R appuser /app
#USER appuser

HEALTHCHECK --start-period=30s --interval=30s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "sh ./startup.sh"]