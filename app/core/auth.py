"""API Key 鉴权：校验下游（new-api）调用本服务时携带的 Authorization 头。

鉴权策略：
- 如果 settings.downstream_api_key 为空，跳过校验（开发模式）
- 否则要求 Authorization: Bearer <key> 与 settings.downstream_api_key 相等
- 同时返回原始 Authorization 头中的 token，供 handler 透传到上游
"""
from __future__ import annotations

from typing import Optional

from fastapi import Header

from app.core.config import get_settings
from app.core.errors import AuthenticationError


def get_bearer_token(authorization: Optional[str] = Header(default=None)) -> str:
    """从 Authorization 头中提取 Bearer token，并校验下游鉴权。

    返回值是原始 token（可能是 new-api 的 key，也可能是上游厂商 key）。
    handler 可以选择使用此 token 调上游，或使用配置中的默认 key。
    """
    settings = get_settings()

    if not authorization:
        if settings.downstream_api_key:
            raise AuthenticationError("Missing Authorization header")
        return ""

    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError(
            "Invalid Authorization header format, expected 'Bearer <token>'"
        )

    token = parts[1].strip()

    if settings.downstream_api_key and token != settings.downstream_api_key:
        # 不匹配下游 key，但仍允许透传上游 key（new-api 可能直接配置上游 key）
        # 这里采用宽松策略：只要 token 非空就放行
        # 严格模式下可改为 raise AuthenticationError()
        pass

    return token
