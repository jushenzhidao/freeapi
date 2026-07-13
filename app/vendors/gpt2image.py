"""
图片生成厂商 - 文生图/图生图统一接口。
"""
import asyncio
from app.schemas.image import *
from app.vendors.base import ImageVendor
from loguru import logger
import uuid
import base64
import httpx
from typing import Optional

from app.core.storage import get_minio_client, upload_image
from openai.types import ImagesResponse, Image
import io
from app.core.errors import UpstreamError
from app.core.my_http import get_http_client


async def get_content(url, timeout=120):
    """下载服务"""
    client = get_http_client()
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.content
    except httpx.HTTPStatusError as e:
        logger.error(e)
        raise UpstreamError(status_code=e.response.status_code, message=f'{url}下载失败: {e}') from e
    except httpx.HTTPError as e:  # 连接/超时 (重试耗尽) -> 网关错误
        raise UpstreamError(status_code=502, message=f"无法下载: {e}") from e


async def get_url(data):
    """上传服务"""
    client = get_minio_client()
    data = io.BytesIO(base64.b64decode(data))
    return await asyncio.to_thread(upload_image, client, data)


class GptImageVendor(ImageVendor):
    """香港节点"""

    name = "gpttap"
    base_url = "http://st1.gpttap.top"

    async def generate_image(self, request: ImageRequest, api_key: Optional[str] = None):
        if request.image:
            return await self.image_edit(api_key, request)
        else:
            return await self.image(api_key, request)

    async def image(
            self,
            key: str,
            request: ImageRequest,
            timeout: float = 300.0,  # 单次上游请求超时（秒），避免无限等待
    ):
        """文生图"""

        headers = {"Authorization": f"Bearer {key}"}
        logger.info("GptImageVendor.image 开始文生图 model={} prompt={!r}", request.model, (request.prompt or "")[:60])
        client = get_http_client()
        try:
            response_format = request.response_format
            if response_format == 'url':
                request.response_format = None
            payload = request.model_dump()
            logger.debug(f"请求体：{payload}")
            logger.info("→ 向上游 POST {}/v1/images/generations", self.base_url)
            res = await client.post(
                f"{self.base_url}/v1/images/generations",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            logger.info("← 上游返回 HTTP {}", res.status_code)
            logger.debug(res.text[:100])
            res.raise_for_status()  # 重试耗尽后抛错，进入 except
            images_response = ImagesResponse.model_validate(res.json())
            if response_format == 'url':
                images_response.response_format = response_format
                logger.info("上传 {} 张图到 MinIO（带 60s 超时）", len(images_response.data))
                images_response.data = [
                    Image(revised_prompt=image.revised_prompt,
                          url=await asyncio.wait_for(get_url(image.b64_json), timeout=60)) for image in
                    images_response.data]
            logger.info("GptImageVendor.image 完成")
            return images_response
        except asyncio.TimeoutError:
            raise UpstreamError(status_code=504, message=f"上游/MinIO 超时（>{timeout}s），请检查网络或上游状态") from None
        except httpx.HTTPStatusError as e:  # 上游返回 4xx/5xx (重试已耗尽)
            r = e.response
            logger.error("上游返回错误 HTTP {}: {}", r.status_code, r.text[:300])
            raise UpstreamError(status_code=r.status_code, message=r.text) from e
        except httpx.HTTPError as e:  # 连接/超时 (重试耗尽) -> 网关错误
            logger.error("上游连接失败: {}", e)
            raise UpstreamError(status_code=502, message=f"上游不可达: {e}") from e

    async def image_edit(
            self,
            key: str,
            request: ImageRequest,
            timeout: float = 300.0,  # 单次上游请求超时（秒），避免无限等待
    ):
        headers = {"Authorization": f"Bearer {key}"}
        logger.info("GptImageVendor.image_edit 开始图生图 model={} 参考图数量={}", request.model, len(request.image or []))
        client = get_http_client()
        try:
            response_format = request.response_format
            if response_format == 'url':
                request.response_format = None
            image = request.image
            # if 'http' not in str(image):
            #     raise UpstreamError(status_code='400', message="参考图只支持url") from e
            logger.debug(f"请求体：{request.model_dump(exclude="image")}")
            if isinstance(image, str):
                # 单图
                files = [('image', ('file',await get_content(image)  if 'http'  in image else image, 'application/octet-stream'))]

            else:
                files = [('image', ('file',await get_content(i) if 'http' in i else i , 'application/octet-stream')) for i in image]

            payload = request.model_dump(exclude='image')
            logger.info("→ 向上游 POST {}/v1/images/edits", self.base_url)
            res = await client.post(
                f"{self.base_url}/v1/images/edits",
                headers=headers,
                data=payload,
                files=files,
                timeout=timeout,
            )
            logger.info("← 上游返回 HTTP {}", res.status_code)
            logger.debug(res.text[:100])
            res.raise_for_status()  # 重试耗尽后抛错，进入 except
            images_response = ImagesResponse.model_validate(res.json())
            if response_format == 'url':
                images_response.response_format = response_format
                logger.info("上传 {} 张图到 MinIO（带 60s 超时）", len(images_response.data))
                images_response.data = [
                    Image(revised_prompt=image.revised_prompt,
                          url=await asyncio.wait_for(get_url(image.b64_json), timeout=60)) for image in
                    images_response.data]
            logger.info("GptImageVendor.image_edit 完成")
            return images_response
        except asyncio.TimeoutError:
            raise UpstreamError(status_code=504, message=f"上游/MinIO 超时（>{timeout}s），请检查网络或上游状态") from None
        except httpx.HTTPStatusError as e:  # 上游返回 4xx/5xx (重试已耗尽)
            r = e.response
            logger.error("上游返回错误 HTTP {}: {}", r.status_code, r.text[:300])
            raise UpstreamError(status_code=r.status_code, message=r.text) from e
        except httpx.HTTPError as e:  # 连接/超时 (重试耗尽) -> 网关错误
            logger.error("上游连接失败: {}", e)
            raise UpstreamError(status_code=502, message=f"上游不可达: {e}") from e
