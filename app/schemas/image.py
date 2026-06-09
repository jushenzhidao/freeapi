"""Image generation schema (OpenAI 兼容)。"""
from __future__ import annotations

from typing import Optional

from app.schemas.common import APIModel


class ImageRequest(APIModel):
    model: str
    prompt: str
    n: int = 1
    size: Optional[str] = None
    quality: Optional[str] = None
    style: Optional[str] = None
    response_format: Optional[str] = None
    user: Optional[str] = None
