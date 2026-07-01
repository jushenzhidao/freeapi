from pydantic import BaseModel, Field
from typing import List, Optional


class ErrorInfo(BaseModel):
    """单张图片生成失败的错误信息"""
    code: Optional[str] = Field(None, description="错误码")
    message: Optional[str] = Field(None, description="错误提示信息")


class DataItem(BaseModel):
    """单张图片信息（成功或失败）"""
    url: Optional[str] = Field(None, description="图片 URL（response_format=url 时返回）")
    b64_json: Optional[str] = Field(None, description="Base64 编码图片（response_format=b64_json 时返回）")
    size: Optional[str] = Field(None, description="图像尺寸，如 2048×2048")
    error: Optional[ErrorInfo] = Field(None, description="生成失败时的错误信息")


class ToolInfo(BaseModel):
    """工具信息"""
    type: Optional[str] = Field(None, description="工具类型，如 web_search")


class ToolUsage(BaseModel):
    """工具用量信息"""
    web_search: Optional[int] = Field(None, description="调用联网搜索工具次数")


class Usage(BaseModel):
    """用量信息"""
    generated_images: Optional[int] = Field(None, description="成功生成的图片张数")
    output_tokens: Optional[int] = Field(None, description="图片花费的 token 数量")
    total_tokens: Optional[int] = Field(None, description="总 token 数量")
    tool_usage: Optional[ToolUsage] = Field(None, description="工具用量信息")


class ErrorResponse(BaseModel):
    """请求错误信息"""
    code: Optional[str] = Field(None, description="错误码")
    message: Optional[str] = Field(None, description="错误提示信息")


class ImagesGenerationsResponse(BaseModel):
    """Seedream 图片生成非流式响应体"""
    model: Optional[str] = Field(None, description="本次请求使用的模型 ID（模型名称-版本）")
    created: Optional[int] = Field(None, description="请求创建时间的 Unix 时间戳（秒）")
    data: Optional[List[DataItem]] = Field(None, description="输出图像的信息数组")
    tools: Optional[List[ToolInfo]] = Field(None, description="本次请求配置的模型调用工具")
    usage: Optional[Usage] = Field(None, description="本次请求的用量信息")
    error: Optional[ErrorResponse] = Field(None, description="本次请求的错误信息")
if __name__ == '__main__':
    x = ImagesGenerationsResponse.model_validate({
    "model": "doubao-seedream-5-0-260128",
    "created": 1757321139,
    "data": [
        {
            "url": "https://",
            "size": "3104x1312"
        }
    ],
    "usage": {
        "generated_images": 1,
        "output_tokens":12,
        "total_tokens": 3
    }
})
    print(x.model)