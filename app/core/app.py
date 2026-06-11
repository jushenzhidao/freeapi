"""FastAPI app 工厂：CORS、错误处理、路由注册。"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="next-api",
        description="AI API aggregation gateway (downstream of new-api)",
        version="0.1.0",
        servers=[{"url": ""}],
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 错误处理
    register_error_handlers(app)

    # 路由（在 create_app 内 import 避免循环引用）
    from app.routes import chat, images, videos,gemini_images

    app.include_router(chat.router, prefix="/v1", tags=["chat"])
    app.include_router(images.router, prefix="/v1", tags=["images"])
    app.include_router(gemini_images.router, prefix="/gemini", tags=["gemini_images"])
    app.include_router(videos.router, prefix="/v1", tags=["videos"])

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
