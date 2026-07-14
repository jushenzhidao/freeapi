"""视频生成 API（OpenAI Sora 兼容）。

POST   /v1/videos              创建视频任务
GET    /v1/videos/{video_id}   查询任务状态
DELETE /v1/videos/{video_id}   取消任务（部分厂商支持）

由于视频是异步任务，且不同厂商的 task_id 格式不同，
查询接口采用以下策略识别厂商：
1. 客户端可在 Header `X-Vendor-Model` 中提供模型名（推荐）
2. 否则尝试通过 task_id 前缀推断（如 cgt- → seedance）
"""
from __future__ import annotations


from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.core.auth import get_bearer_token
from app.core.errors import InvalidRequestError, UpstreamError
from app.core.registry import ServiceType, get_registry
from app.schemas.video import VideoCreateRequest, VideoResponse,GrokVideoCreateRequest
from app.vendors.base import VideoVendor

from loguru import logger
router = APIRouter()

# todo 重写视频
@router.post("/videos")
async def create_video(
    request: GrokVideoCreateRequest,
    api_key: str = Depends(get_bearer_token),
    vendor_url: str = Header(None, alias="X-Request-Vendor"),
):
    registry = get_registry()
    vendor = registry.lookup(ServiceType.VIDEO, request.model)
    if not isinstance(vendor, VideoVendor):
        raise UpstreamError(
            f"Vendor for model '{request.model}' is not a VideoVendor",
            code="invalid_vendor",
        )

    return await vendor.create_video(request, api_key=api_key,base_url=vendor_url)


@router.get("/videos/{video_id}")
async def get_video(
    video_id: str,
    x_vendor_model: Optional[str] = Header(default=None),
    api_key: str = Depends(get_bearer_token),
    vendor_url: str = Header(None, alias="X-Request-Vendor"),
):
    vendor = _resolve_vendor_for_task(video_id, x_vendor_model)
    return await vendor.get_video(video_id, api_key=api_key,base_url=vendor_url)


# @router.delete("/videos/{video_id}", response_model=VideoResponse)
# async def cancel_video(
#     video_id: str,
#     x_vendor_model: Optional[str] = Header(default=None),
#     api_key: str = Depends(get_bearer_token),
# ) -> VideoResponse:
#     vendor = _resolve_vendor_for_task(video_id, x_vendor_model)
#     return await vendor.cancel_video(video_id, api_key=api_key)


def _resolve_vendor_for_task(
    task_id: str,
    model_hint: Optional[str],
) -> VideoVendor:
    """根据 task_id 或客户端提供的模型名推断厂商。

    - model_hint：通过 `X-Vendor-Model` 头传入的模型名
    - task_id 前缀：cgt- → seedance,
    """
    registry = get_registry()

    if model_hint:
        vendor = registry.lookup(ServiceType.VIDEO, model_hint)
        if isinstance(vendor, VideoVendor):
            return vendor

    # 通过 task_id 前缀推断
    inferred_model = _infer_model_from_task_id(task_id)
    if inferred_model:
        try:
            vendor = registry.lookup(ServiceType.VIDEO, inferred_model)
            if isinstance(vendor, VideoVendor):
                return vendor
        except Exception:
            pass

    raise InvalidRequestError(
        f"Cannot determine vendor for task_id '{task_id}'. "
        "Please provide model name via 'X-Vendor-Model' header.",
        code="vendor_not_found",
    )


def _infer_model_from_task_id(task_id: str) -> Optional[str]:
    """根据 task_id 前缀推断对应模型名。"""
    if task_id.startswith("cgt-"):
        return "doubao-seedance"
    return None
