"""
图片生成厂商 - 文生图/图生图统一接口。
"""
import asyncio
from app.schemas.image import *
from app.vendors.base import VideoVendor
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
        raise UpstreamError(status_code=502, message=f"{url}无法下载: {e}") from e


async def get_url(data):
    """上传服务"""
    client = get_minio_client()
    data = io.BytesIO(base64.b64decode(data))
    return await asyncio.to_thread(upload_image, client, data)


class GorkVideoVendor(VideoVendor):


    name = "wxiai"
    # base_url = "http://st1.gpttap.top"

    async def create_video(self, request, api_key,base_url):
        headers = {"Authorization": f"Bearer {api_key}"}
        # logger.info("GptImageVendor.image 开始文生图 model={} prompt={!r}", request.model, (request.prompt or "")[:60])
        client = get_http_client()
        base_url = 'https://api.wxiai.com/xai'
        try:

            logger.info("→ 向上游 POST {}/v1/videos/generations", base_url)
            res = await client.post(
                f"{base_url}/v1/videos/generations",
                headers=headers,
                json=request.model_dump(exclude_none=True),
                # timeout=timeout,
            )
            logger.info("← 上游返回 HTTP {}", res.status_code)
            logger.debug(res.text[:100])
            res.raise_for_status()  # 重试耗尽后抛错，进入 except
            # images_response = ImagesResponse.model_validate(res.json())
            # if response_format == 'url':
            #     images_response.response_format = response_format
            #     logger.info("上传 {} 张图到 MinIO（带 60s 超时）", len(images_response.data))
            #     images_response.data = [
            #         Image(revised_prompt=image.revised_prompt,
            #               url=await asyncio.wait_for(get_url(image.b64_json), timeout=60)) for image in
            #         images_response.data]
            # logger.info("GptImageVendor.image 完成")
            return res.json()
        except asyncio.TimeoutError:
            timeout = 'xxx'
            raise UpstreamError(status_code=504, message=f"上游/MinIO 超时（>{timeout}s），请检查网络或上游状态") from None
        except httpx.HTTPStatusError as e:  # 上游返回 4xx/5xx (重试已耗尽)
            r = e.response
            logger.error("上游返回错误 HTTP {}: {}", r.status_code, r.text[:300])
            raise UpstreamError(status_code=r.status_code, message=r.text) from e
        except httpx.HTTPError as e:  # 连接/超时 (重试耗尽) -> 网关错误
            logger.error("上游连接失败: {}", e)
            raise UpstreamError(status_code=502, message=f"上游不可达: {e}") from e


    async def get_video(self, video_id, api_key, base_url):
        """文生图"""

        headers = {"Authorization": f"Bearer {api_key}"}
        # logger.info("GptImageVendor.image 开始文生图 model={} prompt={!r}", request.model, (request.prompt or "")[:60])
        client = get_http_client()
        base_url = 'https://api.wxiai.com/xai'
        try:

            logger.info("→ 向上游 POST {}/v1/videos/video_id", base_url)
            res = await client.get(
                f"{base_url}/v1/videos/{video_id}",
                headers=headers,
                # json=payload,
                # timeout=timeout,
            )
            logger.info("← 上游返回 HTTP {}", res.status_code)
            logger.debug(res.text[:100])
            res.raise_for_status()  # 重试耗尽后抛错，进入 except
            # images_response = ImagesResponse.model_validate(res.json())
            # if response_format == 'url':
            #     images_response.response_format = response_format
            #     logger.info("上传 {} 张图到 MinIO（带 60s 超时）", len(images_response.data))
            #     images_response.data = [
            #         Image(revised_prompt=image.revised_prompt,
            #               url=await asyncio.wait_for(get_url(image.b64_json), timeout=60)) for image in
            #         images_response.data]
            # logger.info("GptImageVendor.image 完成")
            return res.json()
        except asyncio.TimeoutError:
            timeout = 'xxx'
            raise UpstreamError(status_code=504, message=f"上游/MinIO 超时（>{timeout}s），请检查网络或上游状态") from None
        except httpx.HTTPStatusError as e:  # 上游返回 4xx/5xx (重试已耗尽)
            r = e.response
            logger.error("上游返回错误 HTTP {}: {}", r.status_code, r.text[:300])
            raise UpstreamError(status_code=r.status_code, message=r.text) from e
        except httpx.HTTPError as e:  # 连接/超时 (重试耗尽) -> 网关错误
            logger.error("上游连接失败: {}", e)
            raise UpstreamError(status_code=502, message=f"上游不可达: {e}") from e


