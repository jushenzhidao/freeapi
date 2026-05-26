import time

from fastapi import FastAPI, HTTPException, Request
from starlette.responses import Response
from openai.types import Video, VideoCreateError, VideoSeconds, VideoModel, VideoSize

app = FastAPI(title="Empty API")


@app.post('/v/videos')
async def empty(request: Request) -> Video:
    print("=" * 60)
    print(f"【Method】 {request.method}")
    print(f"【URL】    {request.url}")
    print(f"【Client】 {request.client.host}:{request.client.port if request.client else 'Unknown'}")

    # 1. Query Parameters (URL ?key=value)
    print(f"【Query】  {dict(request.query_params)}")

    # 2. Path Parameters (需在路由中定义才会捕获，如 /debug/params/{id})
    print(f"【Path】   {dict(request.path_params)}")

    # 3. Headers & Cookies
    print(f"【Headers】{dict(request.headers)}")
    print(f"【Cookies】{dict(request.cookies)}")

    # 4. Body (智能识别 JSON / Form / Raw)
    print("【Body】  ", end="")
    content_type = request.headers.get("content-type", "")
    try:
        # Starlette 内部会缓存 body，多次读取安全
        if "application/json" in content_type:
            print("application/json ", end="")
            print(await request.json())
        elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            print("multipart/form-data ", end="")
            print(dict(await request.form()))
        else:
            raw = await request.body()
            print(raw.decode("utf-8", errors="ignore") if raw else "(empty)")
    except Exception as e:
        print(f"(解析失败: {e})")
    print("=" * 60)
    return Video(id='1', completed_at=int(time.time()), created_at=int(time.time() - 30),
                 expires_at=int(time.time() - 30), model='sora-2', progress=100, status='completed', size="1024x1792",
                 seconds="4",object='video')


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=32003)
