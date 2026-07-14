"""Video generation schema (OpenAI Sora 兼容)。

参考 OpenAI Videos API：
- POST /v1/videos          创建视频任务
- GET  /v1/videos/{id}     查询任务状态
- GET  /v1/videos/{id}/content  下载视频内容

任务状态机：queued -> in_progress -> completed | failed
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import Field

from app.schemas.common import APIModel, Usage


VideoStatus = Literal[
    "queued",
    "in_progress",
    "processing",  # 兼容方舟
    "completed",
    "succeeded",  # 兼容方舟
    "failed",
    "cancelled",
]


class VideoCreateRequest(APIModel):
    """创建视频任务的请求体（OpenAI Sora 兼容）。"""

    model: str
    """模型名，例如 doubao-seedance-1-0-pro-250528、sora-2-t2v"""

    prompt: str
    """文本提示词。"""

    seconds: Optional[str] = None
    """视频时长（秒），如 "5", "10"。"""

    size: Optional[str] = None
    """视频分辨率，如 "1280x720", "1920x1080"。"""

    input_reference: Optional[list[str]] = None
    """参考图（URL 数组）。"""

    first_frame_image: Optional[str] = None
    """首帧图（URL 或 base64）。"""

    last_frame_image: Optional[str] = None
    """尾帧图（URL 或 base64）。"""

    n: int = 1
    """生成数量，默认 1。"""

    callback_url: Optional[str] = None
    """异步任务完成后的回调地址。"""

    # 厂商特有参数（可选）
    generate_audio: Optional[bool] = None
    """是否生成音频（部分厂商支持）。"""

    ratio: Optional[str] = None
    """画面比例，如 "16:9", "9:16"。"""

    resolution: Optional[str] = None
    """分辨率，如 "720p", "1080p"。"""

class reference_image(APIModel):
    url: str

class GrokVideoCreateRequest(APIModel):
    """创建视频任务的请求体（OpenAI Sora 兼容）。"""

    model: str
    """模型名，"""

    prompt: str
    """文本提示词。"""

    duration: Optional[int] = None
    """视频时长（秒），如 "5", "10"。"""


    aspect_ratio: Optional[str] = None
    """画面比例，如 "16:9", "9:16"。"""

    resolution: Optional[str] = None
    """分辨率，如 "720p", "1080p"。"""

    reference_images: Optional[list[reference_image]] = None

    image: Optional[reference_image] = None



class VideoError(APIModel):
    code: str
    message: str

class GrokVideoResponse(APIModel):
    """grok视频任务的响应体"""
    request_id:str

class VideoResponse(APIModel):
    """视频任务的响应体（OpenAI Sora 兼容）。"""

    id: str
    object: str = "video"
    model: Optional[str] = None
    status: VideoStatus = "queued"
    progress: int = 0
    created_at: int = 0
    completed_at: Optional[int] = None
    expires_at: Optional[int] = None
    seconds: Optional[str] = None
    size: Optional[str] = None
    video_url: Optional[str] = None
    remixed_from_video_id: Optional[str] = None
    error: Optional[VideoError] = None
    usage: Optional[Usage] = None
    metadata: Optional[dict[str, Any]] = None
