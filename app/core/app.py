"""FastAPI app 工厂：CORS、错误处理、路由注册。"""
from __future__ import annotations
from loguru import logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # 启动逻辑留空，gpt2image 内部懒初始化
    # 关闭：释放 gpt2image 的共享 httpx 客户端
    from app.core.my_http import close_http_client
    await close_http_client()

def configure_logging(level: str) -> None:
    logger.remove()
    logger.add(sys.stderr, level=level)



def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="next-api",
        description="AI API aggregation gateway (downstream of new-api)",
        version="0.1.0",
        servers=[{"url": ""}],
        lifespan=lifespan,
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

    # 请求日志中间件（INFO 级别，默认即可见，解决“调用接口看不到任何日志”）
    @app.middleware("http")
    async def log_requests(request, call_next):
        import time as _time
        _start = _time.perf_counter()
        logger.info("→ {} {}", request.method, request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            _elapsed = (_time.perf_counter() - _start) * 1000
            logger.exception("✗ {} {} 处理异常 ({}ms)", request.method, request.url.path, _elapsed)
            raise
        _elapsed = (_time.perf_counter() - _start) * 1000
        logger.info("← {} {} {} ({}ms)", request.method, request.url.path, response.status_code, _elapsed)
        return response

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
