"""HTTP 客户端：统一的 httpx.AsyncClient 封装，自动处理上游错误。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

import httpx

from app.core.config import get_settings
from app.core.errors import UpstreamError

from loguru import logger


@asynccontextmanager
async def upstream_client(
    base_url: str,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None,
    extra_headers: Optional[dict[str, str]] = None,
) -> AsyncIterator[httpx.AsyncClient]:
    """创建上游 HTTP 客户端的上下文管理器。"""
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
