"""厂商抽象基类。

按服务类型分为四个基类：ChatVendor / ImageVendor / VideoVendor / AudioVendor。
一个厂商类可以同时继承多个基类（例如同一家厂商既支持 chat 也支持 image）。

设计原则：
- handler 只负责"请求转换 + 调上游 + 响应转换"
- 不涉及计费（计费由 new-api 完成）
- 不涉及鉴权（auth 在路由层完成）
- 错误抛出 APIError 子类，全局错误处理器会转为 OpenAI 格式
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Any

from app.schemas.chat import ChatRequest
from app.schemas.image import ImageRequest
from app.schemas.video import VideoCreateRequest, VideoResponse


class BaseVendor(ABC):
    """所有厂商的根基类。"""

    name: str = ""
    """厂商标识，用于日志和错误信息。"""


class ChatVendor(BaseVendor):
    """对话类厂商基类。"""

    @abstractmethod
    async def chat(
        self,
        request: ChatRequest,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> dict | AsyncIterator[dict]:
        """处理对话请求。

        - 非流式：返回 dict（OpenAI ChatCompletion 格式）
        - 流式：返回 AsyncIterator[dict]（每个 chunk 是 ChatCompletionChunk 格式）
        """


class ImageVendor(BaseVendor):
    """图片生成厂商基类。"""

    @abstractmethod
    async def generate_image(
        self,
        request: ImageRequest,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> Any:
        """生成图片，返回 OpenAI ImagesResponse 格式。"""


class VideoVendor(BaseVendor):
    """视频生成厂商基类（异步任务）。"""

    @abstractmethod
    async def create_video(
        self,
        request: VideoCreateRequest,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> VideoResponse:
        """创建视频任务，立即返回 task_id。"""

    @abstractmethod
    async def get_video(
        self,
        video_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> VideoResponse:
        """查询视频任务状态。"""

    async def cancel_video(
        self,
        video_id: str,
        api_key: Optional[str] = None,
    ) -> VideoResponse:
        """取消视频任务（可选实现）。"""
        raise NotImplementedError(f"{self.name} does not support cancel")


class AudioVendor(BaseVendor):
    """语音类厂商基类（TTS/STT）。"""

    async def text_to_speech(
        self, *args, api_key: Optional[str] = None, **kwargs
    ) -> bytes:
        raise NotImplementedError(f"{self.name} does not support TTS")

    async def speech_to_text(
        self, *args, api_key: Optional[str] = None, **kwargs
    ) -> dict:
        raise NotImplementedError(f"{self.name} does not support STT")
