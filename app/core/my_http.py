"""HTTP 客户端：统一的 httpx.AsyncClient 封装，自动处理上游错误。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

import httpx

from app.core.config import get_settings
from app.core.errors import UpstreamError

from loguru import logger
from httpx_retries import Retry, RetryTransport  # 新增

_RETRY = Retry(
    total=3,
    backoff_factor=1.0,  # 退避 ≈ 1s, 2s, 4s...
    backoff_jitter=1.0,  # 随机抖动，防并发重试撞限流的惊群
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"],  # 图生成是 POST，必须显式加
    respect_retry_after_header=True,  # 429 的 Retry-After 优先
)


# ============ 关键修复：进程级共享一个 httpx 客户端，消除每请求新建连接导致的 FD 耗尽 ============
_shared_client: Optional[httpx.AsyncClient] = None

def get_http_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            transport=RetryTransport(retry=_RETRY),
            timeout=httpx.Timeout(1200), # todo 改为环境变量
            limits=httpx.Limits(
                max_connections=100,   # 全项目共用一个池，按总并发调
                max_keepalive_connections=50,
                keepalive_expiry=30,
            ),
        )
    return _shared_client

async def close_http_client() -> None:
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None


@asynccontextmanager
async def upstream_client(
    base_url: str,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None,
    extra_headers: Optional[dict[str, str]] = None,
) -> AsyncIterator[httpx.AsyncClient]:
    """创建上游 HTTP 客户端的上下文管理器。"""
    # todo 示例seedance中用到，后续重构建议消除
    settings = get_settings()
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if extra_headers:
        headers.update(extra_headers)

    async with httpx.AsyncClient(
        base_url=base_url.rstrip("/"),
        headers=headers,
        timeout=timeout or settings.upstream_timeout,
    ) as client:
        yield client


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    json: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """发起请求并返回 JSON。失败时抛出 UpstreamError。"""
    try:
        response = await client.request(method, path, json=json, params=params)
    except httpx.TimeoutException as e:
        raise UpstreamError(f"Upstream timeout: {e}") from e
    except httpx.HTTPError as e:
        raise UpstreamError(f"Upstream connection error: {e}") from e

    if response.status_code >= 400:
        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text}
        message = _extract_upstream_message(payload) or response.text
        logger.warning(
            "Upstream %s %s -> %d: %s", method, path, response.status_code, message
        )
        raise UpstreamError(
            message,
            status_code=response.status_code if response.status_code < 600 else 502,
            code="upstream_error",
        )

    try:
        return response.json()
    except Exception as e:
        raise UpstreamError(f"Upstream returned invalid JSON: {e}") from e


def _extract_upstream_message(payload: Any) -> Optional[str]:
    """尝试从上游错误响应中提取人类可读的消息。"""
    if not isinstance(payload, dict):
        return None
    if isinstance(err := payload.get("error"), dict):
        return err.get("message") or err.get("code")
    if msg := payload.get("message"):
        return str(msg)
    if msg := payload.get("error"):
        return str(msg)
    return None
