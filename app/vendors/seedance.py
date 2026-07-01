"""火山方舟 Seedance 视频生成厂商。

参考：https://www.volcengine.com/docs/82379/1520757

API 端点：
- POST {base}/contents/generations/tasks       创建任务
- GET  {base}/contents/generations/tasks/{id}  查询任务

base_url: https://ark.cn-beijing.volces.com/api/v3

请求格式：
{
    "model": "doubao-seedance-1-0-pro-250528",
    "content": [
        {"type": "text", "text": "prompt --rs 1080p --dur 5"},
        {"type": "image_url", "image_url": {"url": "..."}, "role": "first_frame"}
    ]
}

响应：
- 创建：{"id": "cgt-xxx"}
- 查询：{"id", "model", "status", "content": {"video_url": "..."}, "error": {...}, ...}
  status: queued / running / cancelled / succeeded / failed
"""
from __future__ import annotations

import time
from typing import Any, Optional

from app.core.config import get_settings
from app.core.errors import AuthenticationError, UpstreamError
from app.core.http import request_json, upstream_client
from app.schemas.video import VideoCreateRequest, VideoError, VideoResponse
from app.vendors.base import VideoVendor

from loguru import logger

SEEDANCE_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

# 上游状态 → OpenAI Sora 状态映射
_STATUS_MAP = {
    "queued": "queued",
    "running": "in_progress",
    "succeeded": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}


class SeedanceVideoVendor(VideoVendor):
    """火山方舟 Seedance 视频生成。支持 doubao-seedance-* 系列模型。"""

    name = "seedance"
    base_url = SEEDANCE_BASE_URL

    def _resolve_api_key(self, api_key: Optional[str]) -> str:
        """优先使用客户端传入的 key，其次用配置中的默认 key。"""
        settings = get_settings()
        key = api_key or settings.seedance_api_key
        if not key:
            raise AuthenticationError(
                "Missing Seedance API key. Provide via Authorization header "
                "or set SEEDANCE_API_KEY in environment."
            )
        return key

    def _build_prompt(self, request: VideoCreateRequest) -> str:
        """将 OpenAI Sora 风格参数编码到 prompt 命令行参数中。

        Seedance 通过 prompt 后缀传递参数，例如：
            "a cat dancing --dur 5 --rs 1080p --rt 16:9"
        """
        # 移除已有的 -- 参数
        prompt = request.prompt.split("--", maxsplit=1)[0].strip()

        flags: list[str] = []
        if request.seconds:
            flags.append(f"--dur {request.seconds}")
        if request.ratio:
            flags.append(f"--rt {request.ratio}")
        if request.resolution:
            flags.append(f"--rs {request.resolution}")
        elif request.size:
            # 从 size (1280x720) 推导 resolution
            res = self._size_to_resolution(request.size)
            if res:
                flags.append(f"--rs {res}")

        if flags:
            prompt = f"{prompt} {' '.join(flags)}"
        return prompt

    @staticmethod
    def _size_to_resolution(size: str) -> Optional[str]:
        """1280x720 -> 720p"""
        if not size or "x" not in size:
            return None
        try:
            _, h = size.lower().split("x", 1)
            h_int = int(h)
            if h_int <= 480:
                return "480p"
            if h_int <= 720:
                return "720p"
            if h_int <= 1080:
                return "1080p"
            return "4k"
        except (ValueError, IndexError):
            return None

    def _build_payload(self, request: VideoCreateRequest) -> dict[str, Any]:
        """构造上游请求体。"""
        # 根据是否有图片，自动调整 t2v / i2v 模型变体
        model = request.model
        has_image = bool(
            request.input_reference
            or request.first_frame_image
            or request.last_frame_image
        )
        if "lite" in model and has_image and "t2v" in model:
            model = model.replace("t2v", "i2v")

        payload: dict[str, Any] = {
            "model": model,
            "service_tier": "default",
            "content": [{"type": "text", "text": self._build_prompt(request)}],
        }

        # callback_url
        settings = get_settings()
        callback = request.callback_url or (
            f"{settings.webhook_base_url.rstrip('/')}/seedance"
            if settings.webhook_base_url
            else None
        )
        if callback:
            payload["callback_url"] = callback

        # 音频开关
        if request.generate_audio is not None and "1-5" in model:
            payload["generate_audio"] = request.generate_audio

        # 首帧图
        if request.first_frame_image:
            payload["content"].append({
                "type": "image_url",
                "role": "first_frame",
                "image_url": {"url": request.first_frame_image},
            })

        # 尾帧图
        if request.last_frame_image:
            payload["content"].append({
                "type": "image_url",
                "role": "last_frame",
                "image_url": {"url": request.last_frame_image},
            })

        # 参考图
        for img in request.input_reference or []:
            if not img:
                continue
            payload["content"].append({
                "type": "image_url",
                "role": "reference_image",
                "image_url": {"url": img},
            })

        return payload

    async def create_video(
        self,
        request: VideoCreateRequest,
        api_key: Optional[str] = None,
    ) -> VideoResponse:
        key = self._resolve_api_key(api_key)
        payload = self._build_payload(request)
        logger.info("Seedance create: model=%s prompt=%s", payload["model"], payload["content"][0]["text"][:80])

        async with upstream_client(self.base_url, api_key=key) as client:
            data = await request_json(
                client, "POST", "/contents/generations/tasks", json=payload
            )

        task_id = data.get("id")
        if not task_id:
            raise UpstreamError(f"Seedance returned no task id: {data}")

        return VideoResponse(
            id=task_id,
            model=payload["model"],
            status="queued",
            progress=0,
            created_at=int(time.time()),
            seconds=request.seconds,
            size=request.size,
            metadata={"upstream": "seedance"},
        )

    async def get_video(
        self,
        video_id: str,
        api_key: Optional[str] = None,
    ) -> VideoResponse:
        key = self._resolve_api_key(api_key)

        async with upstream_client(self.base_url, api_key=key) as client:
            data = await request_json(
                client, "GET", f"/contents/generations/tasks/{video_id}"
            )

        return self._to_video_response(data)

    async def cancel_video(
        self,
        video_id: str,
        api_key: Optional[str] = None,
    ) -> VideoResponse:
        key = self._resolve_api_key(api_key)

        async with upstream_client(self.base_url, api_key=key) as client:
            data = await request_json(
                client, "DELETE", f"/contents/generations/tasks/{video_id}"
            )

        return self._to_video_response(data) if data else VideoResponse(
            id=video_id,
            status="cancelled",
            metadata={"upstream": "seedance"},
        )

    @staticmethod
    def _to_video_response(data: dict[str, Any]) -> VideoResponse:
        """上游响应 -> OpenAI Sora 格式。"""
        upstream_status = (data.get("status") or "queued").lower()
        status = _STATUS_MAP.get(upstream_status, upstream_status)

        progress = 0
        if status == "completed":
            progress = 100
        elif status in ("in_progress", "processing"):
            progress = data.get("progress", 50)

        # 视频 URL
        video_url = None
        if (content := data.get("content")) and isinstance(content, dict):
            video_url = content.get("video_url")

        # 错误
        error = None
        if err := data.get("error"):
            if isinstance(err, dict):
                error = VideoError(
                    code=str(err.get("code", "unknown")),
                    message=str(err.get("message", "")),
                )

        # 用量
        usage = None
        if u := data.get("usage"):
            from app.schemas.common import Usage
            usage = Usage(**u) if isinstance(u, dict) else None

        return VideoResponse(
            id=data.get("id", ""),
            model=data.get("model"),
            status=status,
            progress=progress,
            created_at=data.get("created_at", 0),
            completed_at=data.get("updated_at"),
            video_url=video_url,
            error=error,
            usage=usage,
            metadata={"upstream": "seedance", "raw_status": upstream_status},
        )
