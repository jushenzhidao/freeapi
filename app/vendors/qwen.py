"""Qwen 逆向厂商 — 基于 chat.qwen.ai 的对话接口。

工作流程：
1. 使用 email + 固定密码登录获取 token
2. 创建新聊天会话
3. 发送消息并流式/非流式返回响应

认证方式：
- Authorization header 传递 email（作为 api_key 参数传入）
- 密码由服务端固定配置，不对外暴露
"""
from __future__ import annotations

import json
import time
import uuid
from typing import AsyncIterator, Optional

import httpx
from aiostream import await_
from openai.resources.chat.completions import messages

from app.core.errors import UpstreamError
from app.schemas.chat import ChatRequest
from app.vendors.base import ChatVendor

from loguru import logger

# Qwen Web API 配置
QWEN_BASE_URL = "https://chat.qwen.ai"
QWEN_PASSWORD = "058afcb06f9f18d4cace42020bb5b7e0838dca2dae9af002fe0c31c268741269"

QWEN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


class QwenChatVendor(ChatVendor):
    """Qwen 对话厂商（逆向 chat.qwen.ai）。"""

    name = "qwen"

    def _get_client(self) -> httpx.AsyncClient:
        """创建 HTTP 客户端。"""
        return httpx.AsyncClient(
            base_url=QWEN_BASE_URL,
            headers=QWEN_HEADERS,
            timeout=60.0,
        )

    async def chat(
            self,
            request: ChatRequest,
            api_key: Optional[str] = None,
    ) -> dict | AsyncIterator[dict]:
        """处理 Qwen 对话请求。

        api_key 参数实际为 email 地址。
        """
        email = api_key
        if not email:
            raise UpstreamError("Qwen vendor requires email as api_key", code="invalid_api_key")

        if request.stream:
            return self._chat_stream(email, request.messages, request.model)
        else:
            return await self._chat_non_stream(email, request.messages, request.model)

    async def _login_and_create_chat(
            self,
            client: httpx.AsyncClient,
            email: str,
    ) -> tuple[str, str]:
        """登录并创建新聊天会话。"""
        try:
            resp = await client.post(
                "/api/v1/auths/signin",
                json={"email": email, "password": QWEN_PASSWORD},
            )
            resp.raise_for_status()
            token = resp.json()["token"]
        except Exception as e:
            raise UpstreamError(f"Qwen login failed: {e}", code="auth_error") from e

        try:
            chats_resp = await client.post(
                "/api/v2/chats/new",
                json={},
                headers={"Authorization": f"Bearer {token}"},
            )
            chats_resp.raise_for_status()
            chat_id = chats_resp.json()["data"]["id"]
        except Exception as e:
            raise UpstreamError(f"Qwen create chat failed: {e}", code="upstream_error") from e

        return token, chat_id

    def _build_chat_body(
            self,
            messages: list,
            model: str,
            chat_id: str,
            stream: bool = True,
    ) -> dict:
        """构建 Qwen 请求体。"""
        timestamp = int(time.time())
        return {
            "stream": stream,
            "version": "2.1",
            "incremental_output": True,
            "chat_id": chat_id,
            "chat_mode": "normal",
            "model": model,
            "parent_id": None,
            "messages": [
                {
                    "role": msg.role if hasattr(msg, "role") else msg.get("role", "user"),
                    "content": msg.content if hasattr(msg, "content") else msg.get("content", ""),
                    "files": [],
                    "timestamp": timestamp,
                    "chat_type": "t2t",
                    "feature_config": {
                        "thinking_enabled": True,
                        "output_schema": "phase",
                        "research_mode": "normal",
                        "auto_thinking": True,
                        "thinking_mode": "Auto",
                        "thinking_format": "summary",
                        "auto_search": True,
                    },
                    "extra": {"meta": {"subChatType": "t2t"}}
                }
                for msg in messages
            ],
            "timestamp": timestamp,
        }

    def _build_request_headers(self) -> dict:
        """构建请求头。"""
        return {
            "X-Accel-Buffering": "no",
            "X-Request-Id": str(uuid.uuid4()),
            "Version": "0.2.46",
            "source": "web",
        }

    async def _chat_stream(
            self,
            email: str,
            messages: list,
            model: str,
    ) -> AsyncIterator[dict]:
        """流式对话。"""
        async with httpx.AsyncClient(
                base_url=QWEN_BASE_URL,
                headers=QWEN_HEADERS,
                timeout=60.0,
        ) as client:
            token, chat_id = await self._login_and_create_chat(client, email)

            chat_body = self._build_chat_body(messages, model, chat_id, stream=True)
            request_headers = self._build_request_headers()

            try:
                async with client.stream(
                        "POST",
                        f"/api/v2/chat/completions?chat_id={chat_id}",
                        json=chat_body,
                        headers=request_headers,
                ) as resp:
                    resp.raise_for_status()

                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue

                        data_str = line[6:]

                        if data_str == "[DONE]":
                            yield {
                                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": "stop",
                                }],
                            }
                            return

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        choices = data.get("choices")
                        if not choices or not isinstance(choices, list):
                            continue

                        choice_data = choices[0]
                        if not isinstance(choice_data, dict):
                            continue

                        delta = choice_data.get("delta", {})
                        if not isinstance(delta, dict):
                            delta = {"content": str(delta)} if delta else {}

                        finish_reason = choice_data.get("finish_reason")

                        yield {
                            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": delta,
                                "finish_reason": finish_reason,
                            }],
                        }

            except httpx.HTTPStatusError as e:
                raise UpstreamError(
                    f"Qwen API error: {e.response.status_code}",
                    status_code=e.response.status_code,
                    code="upstream_error",
                ) from e
            except httpx.TimeoutException as e:
                raise UpstreamError(f"Qwen API timeout: {e}", code="timeout") from e

    async def _chat_non_stream(
            self,
            email: str,
            messages: list,
            model: str,
    ) -> dict:
        """非流式对话（收集所有 chunk 后返回完整响应）。"""
        full_content = ""

        async for chunk in self._chat_stream(email, messages, model):
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    full_content += content

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": full_content,
                },
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }


if __name__ == '__main__':
    async def xx():
        qwen_c = QwenChatVendor()
        res = await qwen_c.chat(
            request=ChatRequest.model_validate(
                {"stream": False, 'model': 'qwen3.6-plus', 'messages': [{'role': 'user', 'content': '你是谁？'}]}),
            api_key='g3yn9lqty@mail.xiuvi.cn')
        print(res)


    import asyncio

    asyncio.run(xx())
    import pydantic
