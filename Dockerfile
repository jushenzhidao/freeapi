# 使用官方 Python 基础镜像
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

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# ✅ 先只复制依赖文件，利用缓存
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv && \
    uv pip sync uv.lock

ENV PATH="/app/.venv/bin:${PATH}"

# ✅ 再复制源码（这层会变，上面不变）
COPY . /app

RUN adduser -u 5678 --disabled-password --gecos "" appuser && \
    chown -R appuser /app
USER appuser

HEALTHCHECK --start-period=30s --interval=30s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "sh ./startup.sh"]