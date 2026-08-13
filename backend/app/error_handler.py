import logging
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions import AppException

logger = logging.getLogger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    timestamp = datetime.now(timezone.utc).isoformat()
    request_id = request.headers.get("X-Request-ID", "unknown")

    if isinstance(exc, AppException):
        logger.warning(
            "AppException code=%s message=%s request_id=%s",
            exc.code,
            exc.message,
            request_id,
            exc_info=False,
        )
        return JSONResponse(
            status_code=_http_status(exc.code),
            content={
                "code": exc.code,
                "message": exc.message,
                "data": exc.detail,
                "timestamp": timestamp,
                "request_id": request_id,
            },
        )

    logger.exception(
        "Unhandled exception request_id=%s path=%s",
        request_id,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": 5000,
            "message": "系统内部错误",
            "data": None,
            "timestamp": timestamp,
            "request_id": request_id,
        },
    )


def _http_status(code: int) -> int:
    if code == 1000:
        return 400
    elif code in (1001, 1002):
        return 401 if code == 1001 else 403
    elif code == 2000:
        return 400
    elif code == 4004:
        return 404
    return 500
