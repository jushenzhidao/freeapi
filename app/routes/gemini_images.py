"""POST /v1/images/generations"""
from __future__ import annotations

from loguru import logger

from fastapi import APIRouter, Depends, Path
from typing import Annotated
from app.core.auth import get_bearer_token
from app.core.errors import UpstreamError
from app.core.registry import ServiceType, get_registry
from app.schemas.gemini_image import GenerateContentRequest
from app.vendors.seedream2gemini import Seedream2GeminiVendor

router = APIRouter()


@router.post("/v1beta/models/{model}:generateContent")
async def gemini_image_generations(
        request: GenerateContentRequest,
        model: Annotated[str, Path(..., description="模型名称")],
        api_key: Annotated[str, Depends(get_bearer_token)],
):
    registry = get_registry()
    vendor = registry.lookup(ServiceType.GEMINI_IMAGE, model)
    logger.debug(f"model_name:{model}")
    if not isinstance(vendor, Seedream2GeminiVendor):
        raise UpstreamError(
            f"Vendor for model '{model}' is not an ImageVendor",
            code="invalid_vendor",
        )
    request.model_name = model
    return await vendor.generate_image(request, api_key=api_key)
