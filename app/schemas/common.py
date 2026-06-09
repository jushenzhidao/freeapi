"""通用类型。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """所有 API schema 的基类，允许额外字段（向上游透传）。"""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Usage(APIModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
