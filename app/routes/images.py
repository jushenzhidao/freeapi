"""POST /v1/images/generations"""
from __future__ import annotations



from fastapi import APIRouter, Depends,Path

from app.core.auth import get_bearer_token
from app.core.errors import UpstreamError
from app.core.registry import ServiceType, get_registry
from app.schemas.image import ImageRequest
from app.vendors.gpt2image import GptImageVendor
from loguru import logger
router = APIRouter()


@router.post("/images/generations")
async def image_generations(
    request: ImageRequest,
    api_key: str = Depends(get_bearer_token),
):
    registry = get_registry()
    vendor = registry.lookup(ServiceType.IMAGE, request.model)
    if not isinstance(vendor, GptImageVendor):
        raise UpstreamError(
            f"Vendor for model '{request.model}' is not an ImageVendor",
            code="invalid_vendor",
        )

    return await vendor.generate_image(request, api_key=api_key)

