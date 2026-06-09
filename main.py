"""next-api 入口。

启动方式：
- 本地开发：uvicorn main:app --reload --port 8000
- 生产部署（Linux）：
    gunicorn main:app -k uvicorn.workers.UvicornWorker \\
        --bind 0.0.0.0:8000 --workers 2 \\
        --timeout 120 --max-requests 4096 --max-requests-jitter 64
"""
from __future__ import annotations

from app.core.app import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn

    from app.core.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
