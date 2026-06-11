from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal, Dict, Any

"""
GenerateContentResponse
├── candidates?: List[Candidate]                 ← 候选响应列表
│   └── Candidate
│       ├── content?: Content                     ← 生成的内容
│       ├── finishReason?: Literal                 ← 结束原因（18 种枚举）
│       ├── safetyRatings?: List[SafetyRating]     ← 安全评级
│       ├── citationMetadata?: CitationMetadata   ← 引用元数据
│       ├── tokenCount?: int                      ← 令牌计数
│       ├── groundingAttributions?: List[GroundingAttribution]  ← grounding 归因
│       ├── groundingMetadata?: GroundingMetadata   ← grounding 元数据
│       ├── avgLogprobs?: float                    ← 平均对数概率
│       ├── logprobsResult?: LogprobsResult        ← Logprobs 结果
│       ├── urlContextMetadata?: UrlContextMetadata ← URL 上下文
│       ├── index?: int                           ← 候选索引
│       └── finishMessage?: str                     ← 结束消息
│
├── promptFeedback?: PromptFeedback                 ← 提示反馈
├── usageMetadata?: UsageMetadata                  ← 使用元数据（仅输出）
├── modelVersion?: str                              ← 模型版本（仅输出）
├── responseId?: str                                ← 响应 ID（仅输出）
└── modelStatus?: ModelStatus                       ← 模型状态（仅输出）
"""
class Content(BaseModel):
    """生成的内容"""
    role: Optional[str] = Field(None, description="角色")
    parts: List[Dict[str, Any]] = Field(..., description="内容片段数组")


class SafetyRating(BaseModel):
    """安全评级"""
    category: Literal[
        "HARM_CATEGORY_UNSPECIFIED", "HARM_CATEGORY_DEROGATORY",
        "HARM_CATEGORY_TOXICITY", "HARM_CATEGORY_VIOLENCE",
        "HARM_CATEGORY_SEXUAL", "HARM_CATEGORY_MEDICAL",
        "HARM_CATEGORY_DANGEROUS", "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_CIVIC_INTEGRITY"
    ] = Field(..., description="安全类别")
    probability: Literal[
        "HARM_PROBABILITY_UNSPECIFIED", "NEGLIGIBLE", "LOW", "MEDIUM", "HIGH"
    ] = Field(..., description="伤害概率")
    blocked: Optional[bool] = Field(None, description="是否被阻止")


class PromptFeedback(BaseModel):
    """提示反馈"""
    blockReason: Optional[Literal[
        "BLOCK_REASON_UNSPECIFIED", "SAFETY", "OTHER", "BLOCKLIST",
        "PROHIBITED_CONTENT", "IMAGE_SAFETY"
    ]] = Field(None, description="阻止原因")
    safetyRatings: Optional[List[SafetyRating]] = Field(None, description="安全评级列表")


class CitationSource(BaseModel):
    """引用来源"""
    startIndex: Optional[int] = Field(None, description="起始索引")
    endIndex: Optional[int] = Field(None, description="结束索引")
    uri: Optional[str] = Field(None, description="URI")
    license: Optional[str] = Field(None, description="许可证")


class CitationMetadata(BaseModel):
    """引用元数据"""
    citationSources: Optional[List[CitationSource]] = Field(None, description="引用来源列表")


class GroundingPassageId(BaseModel):
    """grounding 段落 ID"""
    passageId: Optional[str] = Field(None, description="段落 ID")
    partIndex: Optional[int] = Field(None, description="片段索引")


class SemanticRetrieverChunk(BaseModel):
    """语义检索片段"""
    source: Optional[str] = Field(None, description="来源")
    chunk: Optional[str] = Field(None, description="片段")


class AttributionSourceId(BaseModel):
    """归因来源 ID"""
    groundingPassage: Optional[GroundingPassageId] = Field(None, description="grounding 段落")
    semanticRetrieverChunk: Optional[SemanticRetrieverChunk] = Field(None, description="语义检索片段")


class GroundingAttribution(BaseModel):
    """grounding 归因"""
    sourceId: Optional[AttributionSourceId] = Field(None, description="来源 ID")
    content: Optional[Content] = Field(None, description="内容")


class Web(BaseModel):
    """Web 来源"""
    uri: Optional[str] = Field(None, description="URI")
    title: Optional[str] = Field(None, description="标题")


class Image(BaseModel):
    """图片来源"""
    sourceUri: Optional[str] = Field(None, description="来源 URI")
    imageUri: Optional[str] = Field(None, description="图片 URI")
    title: Optional[str] = Field(None, description="标题")
    domain: Optional[str] = Field(None, description="域名")


class RetrievedContext(BaseModel):
    """检索上下文"""
    customMetadata: Optional[List[Dict[str, Any]]] = Field(None, description="自定义元数据")
    uri: Optional[str] = Field(None, description="URI")
    title: Optional[str] = Field(None, description="标题")
    text: Optional[str] = Field(None, description="文本")
    fileSearchStore: Optional[str] = Field(None, description="文件搜索存储")


class Maps(BaseModel):
    """地图来源"""
    uri: Optional[str] = Field(None, description="URI")
    title: Optional[str] = Field(None, description="标题")
    text: Optional[str] = Field(None, description="文本")
    placeId: Optional[str] = Field(None, description="地点 ID")
    placeAnswerSources: Optional[Dict[str, Any]] = Field(None, description="地点答案来源")


class GroundingChunk(BaseModel):
    """grounding 片段"""
    web: Optional[Web] = Field(None, description="Web 来源")
    image: Optional[Image] = Field(None, description="图片来源")
    retrievedContext: Optional[RetrievedContext] = Field(None, description="检索上下文")
    maps: Optional[Maps] = Field(None, description="地图来源")


class Segment(BaseModel):
    """片段"""
    partIndex: Optional[int] = Field(None, description="片段索引")
    startIndex: Optional[int] = Field(None, description="起始索引")
    endIndex: Optional[int] = Field(None, description="结束索引")
    text: Optional[str] = Field(None, description="文本")


class GroundingSupport(BaseModel):
    """grounding 支持"""
    groundingChunkIndices: Optional[List[int]] = Field(None, description="grounding 片段索引")
    confidenceScores: Optional[List[float]] = Field(None, description="置信度分数")
    renderedParts: Optional[List[int]] = Field(None, description="渲染片段")
    segment: Optional[Segment] = Field(None, description="片段")


class SearchEntryPoint(BaseModel):
    """搜索入口点"""
    renderedContent: Optional[str] = Field(None, description="渲染内容")
    sdkBlob: Optional[str] = Field(None, description="SDK Blob")


class RetrievalMetadata(BaseModel):
    """检索元数据"""
    googleSearchDynamicRetrievalScore: Optional[float] = Field(None, description="Google 搜索动态检索分数")


class GroundingMetadata(BaseModel):
    """grounding 元数据"""
    groundingChunks: Optional[List[GroundingChunk]] = Field(None, description="grounding 片段列表")
    groundingSupports: Optional[List[GroundingSupport]] = Field(None, description="grounding 支持列表")
    webSearchQueries: Optional[List[str]] = Field(None, description="Web 搜索查询")
    imageSearchQueries: Optional[List[str]] = Field(None, description="图片搜索查询")
    searchEntryPoint: Optional[SearchEntryPoint] = Field(None, description="搜索入口点")
    retrievalMetadata: Optional[RetrievalMetadata] = Field(None, description="检索元数据")
    googleMapsWidgetContextToken: Optional[str] = Field(None, description="Google Maps 小部件上下文令牌")


class LogprobsCandidate(BaseModel):
    """Logprobs 候选"""
    token: Optional[str] = Field(None, description="令牌")
    tokenId: Optional[int] = Field(None, description="令牌 ID")
    logProbability: Optional[float] = Field(None, description="对数概率")


class TopCandidates(BaseModel):
    """Top 候选"""
    candidates: Optional[List[LogprobsCandidate]] = Field(None, description="候选列表")


class LogprobsResult(BaseModel):
    """Logprobs 结果"""
    topCandidates: Optional[List[TopCandidates]] = Field(None, description="Top 候选")
    chosenCandidates: Optional[List[LogprobsCandidate]] = Field(None, description="选中的候选")
    logProbabilitySum: Optional[float] = Field(None, description="对数概率总和")


class UrlMetadata(BaseModel):
    """URL 元数据"""
    retrievedUrl: Optional[str] = Field(None, description="检索到的 URL")
    urlRetrievalStatus: Optional[Literal[
        "URL_RETRIEVAL_STATUS_UNSPECIFIED", "URL_RETRIEVAL_STATUS_SUCCESS",
        "URL_RETRIEVAL_STATUS_ERROR", "URL_RETRIEVAL_STATUS_PAYWALL",
        "URL_RETRIEVAL_STATUS_UNSAFE"
    ]] = Field(None, description="URL 检索状态")


class UrlContextMetadata(BaseModel):
    """URL 上下文元数据"""
    urlMetadata: Optional[List[UrlMetadata]] = Field(None, description="URL 元数据列表")


class ModalityTokenCount(BaseModel):
    """模态令牌计数"""
    modality: Optional[Literal[
        "MODALITY_UNSPECIFIED", "TEXT", "IMAGE", "VIDEO", "AUDIO", "DOCUMENT"
    ]] = Field(None, description="模态")
    tokenCount: Optional[int] = Field(None, description="令牌计数")


class UsageMetadata(BaseModel):
    """使用元数据（仅输出）"""
    promptTokenCount: Optional[int] = Field(None, description="提示令牌计数")
    cachedContentTokenCount: Optional[int] = Field(None, description="缓存内容令牌计数")
    candidatesTokenCount: Optional[int] = Field(None, description="候选令牌计数")
    toolUsePromptTokenCount: Optional[int] = Field(None, description="工具使用提示令牌计数")
    thoughtsTokenCount: Optional[int] = Field(None, description="思考令牌计数")
    totalTokenCount: Optional[int] = Field(None, description="总令牌计数")
    promptTokensDetails: Optional[List[ModalityTokenCount]] = Field(None, description="提示令牌详情")
    cacheTokensDetails: Optional[List[ModalityTokenCount]] = Field(None, description="缓存令牌详情")
    candidatesTokensDetails: Optional[List[ModalityTokenCount]] = Field(None, description="候选令牌详情")
    toolUsePromptTokensDetails: Optional[List[ModalityTokenCount]] = Field(None, description="工具使用提示令牌详情")


class ModelStatus(BaseModel):
    """模型状态（仅输出）"""
    modelStage: Optional[Literal[
        "MODEL_STAGE_UNSPECIFIED", "UNSTABLE_EXPERIMENTAL", "EXPERIMENTAL",
        "PREVIEW", "STABLE", "LEGACY", "DEPRECATED", "RETIRED"
    ]] = Field(None, description="模型阶段")
    retirementTime: Optional[str] = Field(None, description="退役时间")
    message: Optional[str] = Field(None, description="消息")


class Candidate(BaseModel):
    """候选响应"""
    content: Optional[Content] = Field(None, description="生成的内容")
    finishReason: Optional[Literal[
        "FINISH_REASON_UNSPECIFIED", "STOP", "MAX_TOKENS", "SAFETY",
        "RECITATION", "LANGUAGE", "OTHER", "BLOCKLIST", "PROHIBITED_CONTENT",
        "SPII", "MALFORMED_FUNCTION_CALL", "IMAGE_SAFETY", "IMAGE_PROHIBITED_CONTENT",
        "IMAGE_OTHER", "NO_IMAGE", "IMAGE_RECITATION", "UNEXPECTED_TOOL_CALL",
        "TOO_MANY_TOOL_CALLS", "MISSING_THOUGHT_SIGNATURE", "MALFORMED_RESPONSE"
    ]] = Field(None, description="结束原因")
    safetyRatings: Optional[List[SafetyRating]] = Field(None, description="安全评级列表")
    citationMetadata: Optional[CitationMetadata] = Field(None, description="引用元数据")
    tokenCount: Optional[int] = Field(None, description="令牌计数")
    groundingAttributions: Optional[List[GroundingAttribution]] = Field(None, description="grounding 归因列表")
    groundingMetadata: Optional[GroundingMetadata] = Field(None, description="grounding 元数据")
    avgLogprobs: Optional[float] = Field(None, description="平均对数概率")
    logprobsResult: Optional[LogprobsResult] = Field(None, description="Logprobs 结果")
    urlContextMetadata: Optional[UrlContextMetadata] = Field(None, description="URL 上下文元数据")
    index: Optional[int] = Field(None, description="索引")
    finishMessage: Optional[str] = Field(None, description="结束消息")


class GenerateContentResponse(BaseModel):
    """Gemini generateContent 响应体"""
    candidates: Optional[List[Candidate]] = Field(None, description="候选响应列表")
    promptFeedback: Optional[PromptFeedback] = Field(None, description="提示反馈")
    usageMetadata: Optional[UsageMetadata] = Field(None, description="使用元数据")
    modelVersion: Optional[str] = Field(None, description="模型版本")
    responseId: Optional[str] = Field(None, description="响应 ID")
    modelStatus: Optional[ModelStatus] = Field(None, description="模型状态")
if __name__ == '__main__':
    x = GenerateContentResponse.model_validate({
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "text": "Sure, here is a cat: "
                    },
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": "iVBOCTmfMDC"
                        }
                    }
                ],
                "role": "model"
            },
            "finishReason": "STOP",
            "index": 0
        }
    ],
    "usageMetadata": {
        "promptTokenCount": 4,
        "candidatesTokenCount": 1298,
        "totalTokenCount": 1302,
        "promptTokensDetails": [
            {
                "modality": "TEXT",
                "tokenCount": 4
            }
        ],
        "candidatesTokensDetails": [
            {
                "modality": "IMAGE",
                "tokenCount": 1290
            }
        ],
        "serviceTier": "standard"
    },
    "modelVersion": "gemini-2.5-flash-image",
    "responseId": "wnIqavfxEuDUjMcPxMqnCA",
    "turnToken": "v1_ChZ3bklxYXZmeEV1RFVqTWNQeE1xbkNBEhZ3bklxYXZmeEV1RFVqTWNQeE1xbkNB"
})
    print(x.modelVersion)