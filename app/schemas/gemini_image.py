from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union, Literal, Dict, Any
from .common import APIModel

# ==================== Gemini 请求体 ====================

class Blob(BaseModel):
    mimeType: str = Field(..., description="IANA 标准 MIME 类型")
    data: str = Field(..., description="Base64 编码字符串")


class FileData(BaseModel):
    mimeType: Optional[str] = Field(None, description="可选 MIME 类型")
    fileUri: str = Field(..., description="URI")


class Part(BaseModel):
    text: Optional[str] = Field(None, description="内联文本")
    inlineData: Optional[Blob] = Field(None, description="内联媒体字节")
    fileData: Optional[FileData] = Field(None, description="URI 基础数据")


class Content(BaseModel):
    role: Literal["user", "model"] = Field("user", description="user 或 model")
    parts: List[Part] = Field(..., description="内容片段数组")


class SystemInstruction(BaseModel):
    role: Optional[Literal["system"]] = Field("system")
    parts: List[Part] = Field(..., description="系统指令内容")


class ImageConfig(BaseModel):
    aspectRatio: Optional[str] = Field(None, description="宽高比")
    imageSize: Optional[str] = Field(None, description="512, 1K, 2K, 4K")


class GenerationConfig(BaseModel):
    stopSequences: Optional[List[str]] = Field(None)
    responseMimeType: Optional[str] = Field("text/plain")
    responseSchema: Optional[Dict[str, Any]] = Field(None)
    responseJsonSchema: Optional[Dict[str, Any]] = Field(None)
    responseModalities: Optional[List[Literal["TEXT", "IMAGE", "AUDIO"]]] = Field(None)
    candidateCount: Optional[int] = Field(None)
    maxOutputTokens: Optional[int] = Field(None)
    temperature: Optional[float] = Field(None, ge=0, le=2)
    topP: Optional[float] = Field(None)
    topK: Optional[int] = Field(None)
    seed: Optional[int] = Field(None)
    presencePenalty: Optional[float] = Field(None)
    frequencyPenalty: Optional[float] = Field(None)
    responseLogprobs: Optional[bool] = Field(None)
    logprobs: Optional[int] = Field(None, ge=0, le=20)
    enableEnhancedCivicAnswers: Optional[bool] = Field(None)
    speechConfig: Optional[Dict[str, Any]] = Field(None)
    thinkingConfig: Optional[Dict[str, Any]] = Field(None)
    imageConfig: Optional[ImageConfig] = Field(None)
    mediaResolution: Optional[Literal[
        "MEDIA_RESOLUTION_UNSPECIFIED", "MEDIA_RESOLUTION_LOW",
        "MEDIA_RESOLUTION_MEDIUM", "MEDIA_RESOLUTION_HIGH"
    ]] = Field(None)


class SafetySetting(BaseModel):
    category: Literal[...] = Field(...)
    threshold: Literal[...] = Field(...)


class FunctionDeclaration(BaseModel):
    name: str = Field(...)
    description: str = Field(...)
    parameters: Optional[Dict[str, Any]] = Field(None)
    parametersJsonSchema: Optional[Dict[str, Any]] = Field(None)
    response: Optional[Dict[str, Any]] = Field(None)
    responseJsonSchema: Optional[Dict[str, Any]] = Field(None)


class Tool(BaseModel):
    functionDeclarations: Optional[List[FunctionDeclaration]] = Field(None)
    googleSearchRetrieval: Optional[Dict[str, Any]] = Field(None)
    codeExecution: Optional[Dict[str, Any]] = Field(None)
    googleSearch: Optional[Dict[str, Any]] = Field(None)
    computerUse: Optional[Dict[str, Any]] = Field(None)
    urlContext: Optional[Dict[str, Any]] = Field(None)
    fileSearch: Optional[Dict[str, Any]] = Field(None)
    mcpServers: Optional[List[Dict[str, Any]]] = Field(None)
    googleMaps: Optional[Dict[str, Any]] = Field(None)


class FunctionCallingConfig(BaseModel):
    mode: Optional[Literal["AUTO", "ANY", "NONE", "VALIDATED"]] = Field("AUTO")
    allowedFunctionNames: Optional[List[str]] = Field(None)


class ToolConfig(BaseModel):
    functionCallingConfig: Optional[FunctionCallingConfig] = Field(None)
    retrievalConfig: Optional[Dict[str, Any]] = Field(None)
    includeServerSideToolInvocations: Optional[bool] = Field(None)


class GenerateContentRequest(APIModel):
    contents: List[Content] = Field(...)
    systemInstruction: Optional[SystemInstruction] = Field(None)
    generationConfig: Optional[GenerationConfig] = Field(None)
    safetySettings: Optional[List[SafetySetting]] = Field(None)
    tools: Optional[List[Tool]] = Field(None)
    toolConfig: Optional[ToolConfig] = Field(None)
    cachedContent: Optional[str] = Field(None)
    serviceTier: Optional[Literal["unspecified", "standard", "flex", "priority"]] = Field(None)
    store: Optional[bool] = Field(None)



