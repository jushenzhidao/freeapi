import base64
import json
import time
import uuid

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, ChoiceDelta
from openai.types.chat.chat_completion_chunk import Choice as ChoiceChunk
from openai.types.chat.chat_completion import ChatCompletion, Choice, ChatCompletionMessage

app = FastAPI(title="Qwen API")

FIXED_PASSWORD = "058afcb06f9f18d4cace42020bb5b7e0838dca2dae9af002fe0c31c268741269"
BASE_URL = "https://chat.qwen.ai"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def verify_auth(authorization: str) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return authorization[7:]


async def login_and_create_chat(client: httpx.AsyncClient, email: str) -> tuple[str, str]:
    resp = await client.post(
        f"{BASE_URL}/api/v1/auths/signin",
        json={"email": email, "password": FIXED_PASSWORD},
    )
    resp.raise_for_status()
    token = resp.json()["token"]

    chats_resp = await client.post(f"{BASE_URL}/api/v2/chats/new", json={})
    chats_resp.raise_for_status()
    chat_id = chats_resp.json()["data"]["id"]

    return token, chat_id


async def chat_stream_generator(email: str, messages: list, model: str):
    """
    生成器内部管理完整的 httpx 生命周期：
    登录 -> 创建聊天 -> 发送请求 -> 流式读取 -> 关闭连接
    """
    client = httpx.AsyncClient(headers=HEADERS, timeout=60.0)
    try:
        # 1. 登录并创建聊天
        token, chat_id = await login_and_create_chat(client, email)

        timestamp = int(time.time())
        chat_body = {
            "stream": True,
            "version": "2.1",
            "incremental_output": True,
            "chat_id": chat_id,
            "chat_mode": "t2t",
            "model": model,
            "parent_id": None,
            "messages": [
                {
                    "role": msg["role"],
                    "content": msg["content"],
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
                }
                for msg in messages
            ],
            "timestamp": timestamp,
        }

        request_headers = {
            "X-Accel-Buffering": "no",
            "X-Request-Id": str(uuid.uuid4()),
            "Version": "0.2.46",
            "source": "web",
        }

        # 2. 发送流式请求并在生成器内保持连接打开
        async with client.stream(
                "POST",
                f"{BASE_URL}/api/v2/chat/completions?chat_id={chat_id}",
                json=chat_body,
                headers=request_headers,
        ) as resp:
            resp.raise_for_status()

            # 3. 直接在这里迭代流，连接保持打开
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue

                if not line.startswith("data: "):
                    continue

                data_str = line[6:]

                if data_str == "[DONE]":
                    yield "data: [DONE]\n\n"
                    break

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

                chunk = ChatCompletionChunk(
                    id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
                    object="chat.completion.chunk",
                    created=int(time.time()),
                    model=model,
                    choices=[
                        ChoiceChunk(
                            index=0,
                            delta=ChoiceDelta(**delta),
                            finish_reason=finish_reason,
                        )
                    ]
                )

                # SSE 格式输出
                yield f"data: {chunk.model_dump_json()}\n\n"

    finally:
        # 4. 确保连接最终关闭
        await client.aclose()


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    auth = request.headers.get("Authorization", "xxxx")
    email = verify_auth(auth)

    req_body = await request.json()
    messages = req_body.get("messages", [])
    model = req_body.get("model", "qwen3.6-plus")
    stream = req_body.get("stream", False)

    if stream:
        # 返回 StreamingResponse，让 FastAPI 在后台驱动生成器
        return StreamingResponse(
            chat_stream_generator(email, messages, model),
            media_type="text/event-stream",
        )
    else:
        # 非流式：保持原有逻辑，但要确保在 async with 内完成所有读取
        client = httpx.AsyncClient(headers=HEADERS, timeout=60.0)
        try:
            token, chat_id = await login_and_create_chat(client, email)

            timestamp = int(time.time())
            chat_body = {
                "stream": True,
                "version": "2.1",
                "incremental_output": True,
                "chat_id": chat_id,
                "chat_mode": "t2t",
                "model": model,
                "parent_id": None,
                "messages": [
                    {
                        "role": msg["role"],
                        "content": msg["content"],
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
                    }
                    for msg in messages
                ],
                "timestamp": timestamp,
            }

            request_headers = {
                "X-Accel-Buffering": "no",
                "X-Request-Id": str(uuid.uuid4()),
                "Version": "0.2.46",
                "source": "web",
            }

            full_content = ''
            async with client.stream(
                    "POST",
                    f"{BASE_URL}/api/v2/chat/completions?chat_id={chat_id}",
                    json=chat_body,
                    headers=request_headers,
            ) as resp:
                resp.raise_for_status()

                # 必须在 async with 内完成全部读取！
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = data.get("choices")
                    if choices and isinstance(choices, list):
                        choice = choices[0]
                        if isinstance(choice, dict):
                            delta = choice.get("delta", {})
                            if isinstance(delta, dict):
                                content = delta.get("content", "")
                                if content:
                                    full_content += content

            return ChatCompletion(
                id=f"chatcmpl-{uuid.uuid4().hex}",
                model=model,
                choices=[
                    Choice(
                        finish_reason="stop",
                        index=0,
                        message=ChatCompletionMessage(
                            content=full_content,
                            role="assistant"
                        ),
                    )
                ],
                created=int(time.time()),
                object="chat.completion",
            )

        finally:
            await client.aclose()


@app.post("/v1/images/generations")
async def images_generations(request: Request):
    auth = request.headers.get("Authorization", "")
    email = verify_auth(auth)

    req_body = await request.json()
    prompt = req_body.get("prompt", "")
    model = req_body.get("model", "qwen3.6-plus")
    n = req_body.get("n", 1)
    size = req_body.get("size", "16:9")

    client = httpx.AsyncClient(headers=HEADERS, timeout=60.0)
    try:
        token, chat_id = await login_and_create_chat(client, email)

        timestamp = int(time.time())
        chat_body = {
            "stream": True,
            "version": "2.1",
            "incremental_output": True,
            "chat_id": chat_id,
            "chat_mode": "normal",
            "model": model,
            "parent_id": None,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "user_action": "chat",
                    "files": [],
                    "timestamp": timestamp,
                    "models": [model],
                    "chat_type": "t2i",
                    "feature_config": {
                        "thinking_enabled": False,
                        "output_schema": "phase",
                        "research_mode": "normal",
                        "auto_thinking": False,
                        "thinking_mode": "Fast",
                        "auto_search": True,
                    },
                    "extra": {"meta": {"subChatType": "t2i", "size": size}},
                    "sub_chat_type": "t2i",
                }
            ],
            "timestamp": timestamp,
            "size": size,
        }

        request_headers = {
            "X-Accel-Buffering": "no",
            "X-Request-Id": str(uuid.uuid4()),
            "Version": "0.2.46",
            "source": "web",
        }

        image_urls = []
        async with client.stream(
                "POST",
                f"{BASE_URL}/api/v2/chat/completions?chat_id={chat_id}",
                json=chat_body,
                headers=request_headers,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                clean_line = line.strip()
                if not clean_line:
                    continue
                if clean_line.startswith("data: "):
                    data_str = clean_line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if isinstance(data, dict):
                            if "image_url" in data:
                                image_urls.append(data["image_url"])
                            if "choices" in data:
                                for choice in data["choices"]:
                                    delta = choice.get("delta", {})
                                    if "image_url" in delta:
                                        image_urls.append(delta["image_url"])
                            if data.get("content") and isinstance(data["content"], str) and data["content"].startswith(
                                    "http"):
                                image_urls.append(data["content"])
                            if "data" in data and isinstance(data["data"], list):
                                for item in data["data"]:
                                    if "url" in item:
                                        image_urls.append(item["url"])
                    except json.JSONDecodeError:
                        pass

        return {
            "created": timestamp,
            "data": [{"url": url} for url in image_urls[:n]],
        }
    finally:
        await client.aclose()


if __name__ == "__main__":
    uvicorn.run("qwen_fastapi:app", port=32003)