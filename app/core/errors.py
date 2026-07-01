"""错误处理：所有异常统一转为 OpenAI 标准错误格式。

OpenAI 错误格式：
{
    "error": {
        "message": "",
        "type": "invalid_request_error" | "api_error" | "authentication_error" | ,
        "param": null,
        "code": ""
    }
}
"""
from __future__ import annotations
from typing import Any, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from loguru import logger


class APIError(Exception):
    """所有可向客户端暴露的错误的基类，会被转为 OpenAI 错误格式返回。"""

    status_code: int = 500
    error_type: str = "api_error"
    code: Optional[str] = None

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        error_type: Optional[str] = None,
        code: Optional[str] = None,
        param: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_type is not None:
            self.error_type = error_type
        if code is not None:
            self.code = code
        self.param = param


class InvalidRequestError(APIError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_type = "invalid_request_error"


class AuthenticationError(APIError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_type = "authentication_error"


class ModelNotFoundError(APIError):
    status_code = status.HTTP_404_NOT_FOUND
    error_type = "invalid_request_error"
    code = "model_not_found"


class UpstreamError(APIError):
    """上游 API 返回的错误。"""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_type = "api_error"
    code = "upstream_error"


def to_openai_error(
    message: str,
    *,
    error_type: str = "api_error",
    code: Optional[str] = None,
    param: Optional[str] = None,
) -> dict[str, Any]:
    """构造 OpenAI 标准错误响应体。"""
    return {
        "error": {
            "message": message,
            "type": error_type,
            "param": param,
            "code": code,
        }
    }


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=to_openai_error(
            exc.message,
            error_type=exc.error_type,
            code=exc.code,
            param=exc.param,
        ),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    error_type = (
        "authentication_error"
        if exc.status_code == 401
        else "invalid_request_error"
        if 400 <= exc.status_code < 500
        else "api_error"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=to_openai_error(str(exc.detail), error_type=error_type),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {}
    loc = first.get("loc", [])
    param = ".".join(str(p) for p in loc[1:]) if len(loc) > 1 else None
    msg = first.get("msg", "Invalid request")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=to_openai_error(
            f"{msg}" + (f" (param: {param})" if param else ""),
            error_type="invalid_request_error",
            param=param,
        ),
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=to_openai_error(
            "Internal server error",
            error_type="api_error",
            code="internal_error",
        ),
    )


def register_error_handlers(app) -> None:
    """注册所有错误处理器到 FastAPI app。"""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
