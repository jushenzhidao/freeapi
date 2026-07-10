"""
图片生成厂商 - 文生图/图生图统一接口。
"""
from pydantic_settings.sources.providers import aws

from app.schemas.image import *
from app.vendors.base import ImageVendor
from loguru import logger
import uuid
import base64
import httpx
from typing import Optional, List
from httpx_retries import Retry, RetryTransport  # 新增
from app.core.storage import get_minio_client,upload_image
from openai.types import ImagesResponse,Image
import  io
from app.core.errors import UpstreamError
_RETRY = Retry(
    total=3,
    backoff_factor=1.0,  # 退避 ≈ 1s, 2s, 4s...
    backoff_jitter=1.0,  # 随机抖动，防并发重试撞限流的惊群
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"],  # 图生成是 POST，必须显式加
    respect_retry_after_header=True,  # 429 的 Retry-After 优先
)


def _client(timeout: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=RetryTransport(retry=_RETRY),
        timeout=httpx.Timeout(timeout),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),  # 承接高并发
    )

async def get_content(url,timeout=30):
    """下载服务"""
    async with _client(timeout) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            logger.error(e)
            raise UpstreamError(e.response.status_code,message=f'{url}下载失败: {e}') from e
        except httpx.HTTPError as e:  # 连接/超时 (重试耗尽) -> 网关错误
            raise UpstreamError(502, str(e), f"无法下载: {e}") from e

async def get_url(data):
    """上传服务"""
    client = get_minio_client()
    data = io.BytesIO(base64.b64decode(data))
    return upload_image(client, data)


class GPTIMAGE(ImageVendor):
    """香港节点"""

    name = "gpttap"
    base_url = "http://st1.gpttap.top"

    async def generate_image(self, request: ImageRequest, api_key: Optional[str] = None):
        if request.image:
            return self.image_edit(api_key,request)
        else:
            return self.image(api_key, request)
    async def image(
            self,
            key: str,
            request: ImageRequest,
            timeout: float = 3000,  # 图生成慢，给足超时
    ):
        """文生图"""

        headers = {"Authorization": f"Bearer {key}"}

        async with _client(timeout) as client:
            try:
                response_format = request.response_format
                if response_format=='url':
                    request.response_format = None
                payload = request.model_dump()
                res = await client.post(
                    f"{self.base_url}/v1/images/generations",
                    headers=headers,
                    json=payload,
                )
                logger.debug(res.text[:100])
                res.raise_for_status()  # 重试耗尽后抛错，进入 except
                images_response = ImagesResponse.model_validate(res.json())
                if response_format=='url':
                    images_response.response_format = response_format
                    images_response.data = [Image(revised_prompt=image.revised_prompt,url = await get_url(image.b64_json)) for image in images_response.data]
                return images_response
            except httpx.HTTPStatusError as e:  # 上游返回 4xx/5xx (重试已耗尽)
                r = e.response
                raise UpstreamError(r.status_code, r.text) from e
            except httpx.HTTPError as e:  # 连接/超时 (重试耗尽) -> 网关错误
                raise UpstreamError(502, str(e), f"上游不可达: {e}") from e

    async def image_edit(
            self,
            key: str,
            request: ImageRequest,
            timeout: float = 3000,  # 图生成慢，给足超时
    ):
        headers = {"Authorization": f"Bearer {key}"}

        async with _client(timeout) as client:
            try:
                response_format = request.response_format
                if response_format == 'url':
                    request.response_format = None
                image = request.image
                if isinstance(str,image):
                    '单图'
                    files = [('image',('file',get_content(image),'application/octet-stream')) ]

                else:
                    files = [('image', ('file', get_content(i), 'application/octet-stream')) for i in image]

                payload = request.model_dump()
                res = await client.post(
                    f"{self.base_url}/v1/images/generations",
                    headers=headers,
                    json=payload,
                    files=files
                )
                logger.debug(res.text[:100])
                res.raise_for_status()  # 重试耗尽后抛错，进入 except
                images_response = ImagesResponse.model_validate(res.json())
                if response_format == 'url':
                    images_response.response_format = response_format
                    images_response.data = [
                        Image(revised_prompt=image.revised_prompt, url=await get_url(image.b64_json)) for image in
                        images_response.data]
                return images_response
            except httpx.HTTPStatusError as e:  # 上游返回 4xx/5xx (重试已耗尽)
                r = e.response
                raise UpstreamError(r.status_code, r.text) from e
            except httpx.HTTPError as e:  # 连接/超时 (重试耗尽) -> 网关错误
                raise UpstreamError(502, str(e), f"上游不可达: {e}") from e