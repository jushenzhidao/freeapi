"""Chat completions schema (OpenAI 兼容)。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from app.schemas.common import APIModel


class ChatMessage(APIModel):
    role: str
    content: Any
    name: Optional[str] = None
    tool_calls: Optional[list[Any]] = None
    tool_call_id: Optional[str] = None


class ChatRequest(APIModel):
    model: str
    messages: list[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: bool = False
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    stop: Optional[list[str] | str] = None
    tools: Optional[list[Any]] = None
    tool_choice: Optional[Any] = None
    user: Optional[str] = None
