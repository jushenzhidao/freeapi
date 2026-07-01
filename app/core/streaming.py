"""SSE 流式响应工具。

参考 meutils 中 create_chat_completion_chunk 的模式：
- handler 返回 AsyncGenerator[ChatCompletionChunk]（流式）或 dict（非流式）
- 路由层用 sse_event_stream 包装为 SSE 格式
"""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator, AsyncIterator, Iterable

from sse_starlette.sse import EventSourceResponse

from loguru import logger


async def sse_event_stream(
    chunks: AsyncIterator[Any] | Iterable[Any],
    *,
    done_marker: str = "[DONE]",
) -> AsyncGenerator[dict[str, str], None]:
    """将异步/同步 chunk 流转为 SSE 事件流。

    每个 chunk 会被序列化为 JSON 后作为 `data` 字段发送。
    流结束时发送 `data: [DONE]`。
    """
    try:
        if hasattr(chunks, "__aiter__"):
            async for chunk in chunks:  # type: ignore[union-attr]
                yield {"data": _serialize(chunk)}
        else:
            for chunk in chunks:  # type: ignore[union-attr]
                yield {"data": _serialize(chunk)}
    except Exception as e:
        logger.exception("Stream error: %s", e)
        err_payload = {
            "error": {
                "message": str(e),
                "type": "api_error",
                "code": "stream_error",
            }
        }
        yield {"data": json.dumps(err_payload, ensure_ascii=False)}
    finally:
        yield {"data": done_marker}


def _serialize(chunk: Any) -> str:
    """将 chunk 序列化为 JSON 字符串。"""
    if isinstance(chunk, str):
        return chunk
    if hasattr(chunk, "model_dump"):
        chunk = chunk.model_dump(exclude_none=True)
    elif hasattr(chunk, "dict"):
        chunk = chunk.dict(exclude_none=True)  # type: ignore[attr-defined]
    return json.dumps(chunk, ensure_ascii=False, default=str)


def stream_response(chunks: AsyncIterator[Any] | Iterable[Any]) -> EventSourceResponse:
    """便捷函数：将 chunks 流包装为 EventSourceResponse。"""
    return EventSourceResponse(sse_event_stream(chunks))
