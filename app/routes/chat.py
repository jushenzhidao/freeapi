"""POST /v1/chat/completions"""
from __future__ import annotations

import inspect


from fastapi import APIRouter, Depends

from app.core.auth import get_bearer_token
from app.core.errors import UpstreamError
from app.core.registry import ServiceType, get_registry
from app.core.streaming import stream_response
from app.schemas.chat import ChatRequest
from app.vendors.base import ChatVendor
from loguru import logger

router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(
    request: ChatRequest,
    api_key: str = Depends(get_bearer_token),
):
    registry = get_registry()
    vendor = registry.lookup(ServiceType.CHAT, request.model)
    if not isinstance(vendor, ChatVendor):
        raise UpstreamError(
            f"Vendor for model '{request.model}' is not a ChatVendor",
            code="invalid_vendor",
        )

    response = await vendor.chat(request, api_key=api_key)

    # 流式：返回 AsyncIterator
    if request.stream and (inspect.isasyncgen(response) or hasattr(response, "__aiter__")):
        return stream_response(response)

    return response
