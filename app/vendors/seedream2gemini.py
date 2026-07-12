"""seedream 转换为 gemini接口

工作流程：
1. 接受gemini风格的请求体
2. 转换为seedream风格
3. 调用seedream接口
4. 响应转换为gemini风格

认证方式：
- Authorization header 传递 email（作为 api_key 参数传入）
- 密码由服务端固定配置，不对外暴露
"""
from app.schemas.gemini_image import *
from app.schemas.gemini_image_response import *
from app.schemas.seedream_response import *
from app.schemas.seedream import *
from app.vendors.base import ImageVendor
from httpx import AsyncClient
from loguru import logger

class Seedream2GeminiVendor(ImageVendor):
    """seedream 转为 gemini"""

    name = "seedream2gemini"
    base_url = "https://ark.cn-beijing.volces.com/api/v3"

    async def generate_image(
            self,
            request: GenerateContentRequest,
            api_key: Optional[str] = None,
    ) -> GenerateContentResponse:
        model_name = request.model_name
        volc_req = await self.gemini_to_seedream(request, target_model=model_name)
        volc_req_json = volc_req.model_dump()
        logger.debug(f'body参数：\n{volc_req_json}')
        async with AsyncClient(timeout=6000) as client:
            headers = {"Authorization": f"Bearer {api_key}",'Content-Type': 'application/json'}

            response = await client.post(self.base_url + '/images/generations',json=volc_req_json,headers=headers)
            logger.debug(response.status_code)
            response.raise_for_status()
            # logger.debug(response.text)
            seedream_resp = response.json()
        # logger.info(seedream_resp)
        SR = ImagesGenerationsResponse.model_validate(seedream_resp)
        GR = await self.seedream_to_gemini(SR)
        return GR
    #     https://ark.cn-beijing.volces.com/api/v3/images/generations

    async def gemini_to_seedream(
            self,
            gemini_req: GenerateContentRequest,
            target_model: str = "doubao-seedream-5.0-lite",
            response_format: Literal["url", "b64_json"] = "b64_json",
            watermark: bool = False,
            stream: bool = False,
            output_format: Optional[Literal["png", "jpeg"]] = "jpeg",
            inject_size_hint_in_prompt: bool = True,
    ) -> VolcImagesGenerationsRequest:
        """
        Gemini → Seedream 请求体映射函数

        核心映射：
        - contents[].text → prompt (合并)
        - systemInstruction → prompt 前缀
        - inlineData → image (data URI)
        - fileData → image (URL)  ✅ 修正：支持 URL 引用
        - imageConfig → size + prompt 注入
        - googleSearch/googleSearchRetrieval → web_search (仅 5.0-lite)
        - temperature → guidance_scale (仅 3.0-t2i)
        - 其余全部丢弃
        """

        # 验证
        if not target_model or not target_model.strip():
            raise ValueError("target_model 不能为空")
        target_model = target_model.strip()

        if not gemini_req.contents:
            raise ValueError("contents 不能为空")

        user_contents = [c for c in gemini_req.contents if c.role == "user"]
        if not user_contents:
            raise ValueError("必须至少包含一个 user role")

        # 提取 systemInstruction
        system_prompt = ""
        if gemini_req.systemInstruction and gemini_req.systemInstruction.parts:
            texts = [p.text.strip() for p in gemini_req.systemInstruction.parts if p.text]
            system_prompt = " ".join(texts)

        # 提取 user prompt
        prompt_parts = []
        for content in user_contents:
            for part in content.parts:
                if part.text and part.text.strip():
                    prompt_parts.append(part.text.strip())

        user_prompt = " ".join(prompt_parts)
        if not user_prompt and not system_prompt:
            raise ValueError("未找到有效的 prompt 文本")

        # 合并 prompt
        if system_prompt:
            prompt = f"[系统指令] {system_prompt}\n\n[用户请求] {user_prompt}" if user_prompt else system_prompt
        else:
            prompt = user_prompt

        # 提取参考图片（inlineData + fileData）
        images = []
        for content in user_contents:
            for part in content.parts:
                if part.inlineData:
                    # inlineData → data URI
                    data = part.inlineData.data.strip()
                    if data.startswith("data:") and ";base64," in data:
                        data = data.split(";base64,")[1]
                    images.append(f"data:{part.inlineData.mimeType};base64,{data}")
                elif part.fileData:
                    # fileData → URL  ✅ 修正：Seedream 支持 URL
                    images.append(part.fileData.fileUri)

        image = None
        if len(images) == 1:
            image = images[0]
        elif len(images) >= 2:
            if len(images) > 14:
                raise ValueError(f"参考图 {len(images)} 张超过上限 14")
            image = images

        # 解析图像配置
        config = gemini_req.generationConfig.imageConfig if gemini_req.generationConfig else None
        aspect_ratio = "1:1"
        image_size = "2K"

        if config:
            aspect_ratio = config.aspectRatio if config.aspectRatio in ASPECT_RATIO_TO_SIZE.get("2K", {}) else "1:1"
            image_size = config.imageSize or "2K"

        # 1K/3K 兼容性
        if image_size == "1K" and target_model not in MODEL_SUPPORTS_1K:
            image_size = "2K"
        if image_size == "3K" and target_model not in MODEL_SUPPORTS_3K:
            image_size = "2K"

        # 映射 size
        size = "2048x2048"
        if config:
            if image_size in IMAGE_SIZE_MAP:
                size = IMAGE_SIZE_MAP[image_size]
            else:
                pixel_size = ASPECT_RATIO_TO_SIZE.get(image_size, {}).get(aspect_ratio)
                if pixel_size:
                    size = pixel_size

        # 自然语言注入
        if inject_size_hint_in_prompt and config:
            if not any(kw in prompt for kw in SIZE_KEYWORDS):
                prompt = f"生成{aspect_ratio}宽高比、{image_size}分辨率的图片。{prompt}"

        # 构建 Seedream 请求
        volc_req = VolcImagesGenerationsRequest(
            model=target_model,
            prompt=prompt,
            image=image,
            size=size,
            response_format=response_format,
            watermark=watermark,
            stream=stream,
            output_format=output_format,
        )

        return volc_req
    async def seedream_to_gemini(
            self,
        seedream_resp: ImagesGenerationsResponse

    ) -> GenerateContentResponse:
        """
        Seedream 非流式响应 → Gemini GenerateContentResponse
        """



        candidates = []

        # 1. data 数组 → candidates
        if seedream_resp.data:
            for idx, item in enumerate(seedream_resp.data):
                # 1.1 生成失败
                if item.error:
                    finish_reason = "SAFETY" if "safety" in (item.error.message or "").lower() else "OTHER"
                    candidate = Candidate(
                        content=Content(
                            role="model",
                            parts=[{"text": f"生成失败: {item.error.message}"}]
                        ),
                        finishReason=finish_reason,
                        finishMessage=item.error.message,
                        index=idx,
                    )
                    candidates.append(candidate)
                    continue

                # 1.2 生成成功
                parts = []

                # b64_json → inlineData
                if item.b64_json:
                    parts.append({
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": item.b64_json
                        }
                    })
                elif item.url:
                    parts.append({"text": f"{item.url}"})

                # size → text
                # if item.size:
                #     parts.append({"text": f"图片尺寸: {item.size}"})

                candidate = Candidate(
                    content=Content(role="model", parts=parts),
                    finishReason="STOP",
                    index=idx,
                )
                candidates.append(candidate)

        # 2. 请求级错误 → promptFeedback
        prompt_feedback = None
        if seedream_resp.error:
            prompt_feedback = PromptFeedback(
                blockReason="SAFETY" if "safety" in (seedream_resp.error.message or "").lower() else "OTHER",
                safetyRatings=[SafetyRating(
                    category="HARM_CATEGORY_UNSPECIFIED",
                    probability="HIGH",
                    blocked=True
                )]
            )

        # 3. usage → usageMetadata（修正映射）
        usage_metadata = None
        if seedream_resp.usage:
            usage_metadata = UsageMetadata(
                # Seedream output_tokens → Gemini candidatesTokenCount
                candidatesTokenCount=seedream_resp.usage.output_tokens,
                # Seedream total_tokens → Gemini totalTokenCount
                totalTokenCount=seedream_resp.usage.total_tokens,
                # 注意：promptTokenCount 和 toolUsePromptTokenCount 无法从 Seedream 获取
                # 因为 Seedream 不返回输入 token 和工具 token 的明细
                promptTokenCount=None,
                toolUsePromptTokenCount=None,
            )

        # 4. 构建响应
        return GenerateContentResponse(
            candidates=candidates if candidates else None,
            promptFeedback=prompt_feedback,
            usageMetadata=usage_metadata,
            modelVersion=seedream_resp.model,

        )
if __name__ == '__main__':
#     x = Seedream2GeminiVendor()
#     seedream_resp =  ImagesGenerationsResponse.model_validate({
#     "model": "doubao-seedream-5-0-260128",
#     "created": 1757321139,
#     "data": [
#         {
#             "url": "https://...",
#             "size": "3104x1312"
#         }
#     ],
#     "usage": {
#         "generated_images": 1,
#         "output_tokens":12,
#         "total_tokens": 3
#     }
# })
#     import asyncio
#     t = asyncio.run(x.seedream_to_gemini(seedream_resp))
#     print(t)
#     # print(x.seedream_to_gemini(seedream_resp))
    from httpx import Client
    import json
    x = json.loads('''{"model":"doubao-seedream-5-0-260128","prompt":"生成16:9宽高比、2K分辨率的图片。draw a cat","image":null,"size":"2K","sequential_image_generation":"disabled","sequential_image_generation_options":null,"tools":null,"stream":false,"guidance_scale":null,"output_format":"jpeg","response_format":"b64_json","watermark":false,"optimize_prompt_options":null}''')
    with Client(timeout=600) as client:
        api_key = 'ark-99c5a49a-4505-409d-a43d-6494761b60a4-8055c'
        base_url = 'https://ark.cn-beijing.volces.com/api/v3'
        headers = {"Authorization": f"Bearer {api_key}", 'Content-Type': 'application/json'}
        response = client.post(base_url + '/images/generations', json=x, headers=headers)
        response.raise_for_status()
        seedream_resp = response.json()
    print(seedream_resp)
