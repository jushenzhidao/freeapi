import uvicorn
from fastapi import FastAPI, Request

from loguru import logger


app = FastAPI(title="IP API")


@app.get("/ip")
async def chat_completions(request: Request):
    client_ip = request.client.host
    logger.info(client_ip)
    return {'ip':client_ip}


if __name__ == "__main__":
    uvicorn.run("qwen_fastapi:app", port=32003)