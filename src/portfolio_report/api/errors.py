"""API 예외 + HTTPException 매퍼.

도메인 코드는 일반적으로 `ValueError` 또는 자유로운 `Exception`을 던진다.
API 경계에서 일관된 `{error, message}` JSON 응답으로 변환한다.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class APIError(Exception):
    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code


class TickerNotFoundError(APIError):
    status_code = 404
    error_code = "ticker_not_found"


class UpstreamUnavailableError(APIError):
    status_code = 503
    error_code = "upstream_unavailable"


def _json(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": error, "message": message}
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api_error(_request: Request, exc: APIError) -> JSONResponse:
        return _json(exc.status_code, exc.error_code, exc.message)

    @app.exception_handler(ValueError)
    async def _value_error(_request: Request, exc: ValueError) -> JSONResponse:
        # TickerResolver가 종목을 찾지 못하면 ValueError를 던진다
        return _json(404, "ticker_not_found", str(exc))

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return _json(422, "validation_error", str(exc.errors()))

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("처리되지 않은 예외")
        return _json(500, "internal_error", str(exc))
