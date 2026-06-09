"""Qwen 厂商测试（mock 上游 API）。"""
from __future__ import annotations

import json
import pytest
import respx
from httpx import Response

from app.schemas.chat import ChatRequest, ChatMessage
from app.vendors.qwen import QwenChatVendor, QWEN_BASE_URL


@pytest.fixture
def vendor():
    return QwenChatVendor()


def test_build_chat_body(vendor):
    messages = [
        ChatMessage(role="user", content="hello"),
    ]
    body = vendor._build_chat_body(messages, "qwen-plus", "test-chat-id", stream=True)
    assert body["model"] == "qwen-plus"
    assert body["chat_id"] == "test-chat-id"
    assert body["stream"] is True
    assert len(body["messages"]) == 1
    assert body["messages"][0]["content"] == "hello"


def test_build_request_headers(vendor):
    headers = vendor._build_request_headers()
    assert "X-Request-Id" in headers
    assert headers["source"] == "web"
    assert headers["Version"] == "0.2.46"


@pytest.mark.asyncio
@respx.mock
async def test_login_success(vendor):
    respx.post(f"{QWEN_BASE_URL}/api/v1/auths/signin").mock(
        return_value=Response(200, json={"token": "test-token-123"})
    )
    respx.post(f"{QWEN_BASE_URL}/api/v2/chats/new").mock(
        return_value=Response(200, json={"data": {"id": "chat-abc"}})
    )

    async with vendor._get_client() as client:
        token, chat_id = await vendor._login_and_create_chat(client, "test@example.com")
        assert token == "test-token-123"
        assert chat_id == "chat-abc"


@pytest.mark.asyncio
@respx.mock
async def test_login_failure(vendor):
    respx.post(f"{QWEN_BASE_URL}/api/v1/auths/signin").mock(
        return_value=Response(401, json={"error": "Invalid credentials"})
    )

    async with vendor._get_client() as client:
        from app.core.errors import UpstreamError
        with pytest.raises(UpstreamError) as exc_info:
            await vendor._login_and_create_chat(client, "bad@example.com")
        assert "login failed" in str(exc_info.value).lower()


@pytest.mark.asyncio
@respx.mock
async def test_chat_without_email_raises():
    vendor = QwenChatVendor()
    req = ChatRequest(
        model="qwen-plus",
        messages=[ChatMessage(role="user", content="hi")],
    )
    from app.core.errors import UpstreamError
    with pytest.raises(UpstreamError) as exc_info:
        await vendor.chat(req, api_key=None)
    assert "email" in str(exc_info.value).lower()
