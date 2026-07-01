
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union, Literal, Dict, Any
# ==================== Seedream 请求体 ====================

class VolcSequentialImageGenerationOptions(BaseModel):
    max_images: int = Field(15, ge=1, le=15)


class VolcTool(BaseModel):
    type: Literal["web_search"] = Field()


class VolcOptimizePromptOptions(BaseModel):
    mode: Literal["standard", "fast"] = Field("standard")


class VolcImagesGenerationsRequest(BaseModel):
    model: str = Field()
    prompt: str = Field()
    image: Optional[Union[str, List[str]]] = Field(None)
    size: Optional[str] = Field("2048x2048")
    sequential_image_generation: Optional[Literal["auto", "disabled"]] = Field("disabled")
    sequential_image_generation_options: Optional[VolcSequentialImageGenerationOptions] = Field(None)
    tools: Optional[List[VolcTool]] = Field(None)
    stream: Optional[bool] = Field(False)
    guidance_scale: Optional[float] = Field(None, ge=1, le=10)
    output_format: Optional[Literal["png", "jpeg"]] = Field("jpeg")
    response_format: Optional[Literal["url", "b64_json"]] = Field("url")
    watermark: Optional[bool] = Field(True)
    optimize_prompt_options: Optional[VolcOptimizePromptOptions] = Field(None)

    @field_validator("image")
    @classmethod
    def validate_image_array(cls, v):
        if isinstance(v, list) and not (2 <= len(v) <= 14):
            raise ValueError("多图输入时，图片数量必须在 2-14 张之间")
        return v


# ==================== 映射配置 ====================

MODEL_SUPPORTS_1K = {"doubao-seedream-4.0"}
MODEL_SUPPORTS_3K = {"doubao-seedream-5.0-lite", "doubao-seedream-4.5", "doubao-seedream-4.0"}
MODEL_SUPPORTS_GROUP = {"doubao-seedream-5.0-lite", "doubao-seedream-4.5", "doubao-seedream-4.0"}
MODEL_SUPPORTS_TOOLS = {"doubao-seedream-5.0-lite"}
MODEL_SUPPORTS_FAST_OPTIMIZE = {"doubao-seedream-4.0"}
MODEL_SUPPORTS_GUIDANCE_SCALE = {"doubao-seedream-3.0-t2i"}

IMAGE_SIZE_MAP = {"1K": "1K", "2K": "2K", "4K": "4K"}

ASPECT_RATIO_TO_SIZE = {
    "1K": {"1:1": "1024x1024", "2:3": "832x1248", "3:2": "1248x832", "3:4": "864x1152",
           "4:3": "1152x864", "4:5": "1024x1280", "5:4": "1280x1024", "9:16": "800x1424",
           "16:9": "1424x800", "21:9": "1568x672"},
    "2K": {"1:1": "2048x2048", "2:3": "1664x2496", "3:2": "2496x1664", "3:4": "1728x2304",
           "4:3": "2304x1728", "4:5": "2048x2560", "5:4": "2560x2048", "9:16": "1600x2848",
           "16:9": "2848x1600", "21:9": "3136x1344"},
    "3K": {"1:1": "3072x3072", "2:3": "2496x3744", "3:2": "3744x2496", "3:4": "2592x3456",
           "4:3": "3456x2592", "4:5": "3072x3840", "5:4": "3840x3072", "9:16": "2304x4096",
           "16:9": "4096x2304", "21:9": "4704x2016"},
    "4K": {"1:1": "4096x4096", "2:3": "3328x4992", "3:2": "4992x3328", "3:4": "3520x4704",
           "4:3": "4704x3520", "4:5": "4096x5120", "5:4": "5120x4096", "9:16": "3040x5504",
           "16:9": "5504x3040", "21:9": "6240x2656"},
}

SIZE_KEYWORDS = ["分辨率", "像素", "宽高比", "比例", "尺寸", "大小",
                 "1K", "2K", "3K", "4K", "1:1", "16:9", "9:16", "4:3", "3:4", "2:3", "3:2"]