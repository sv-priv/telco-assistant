"""RFC 9457 Problem Details for HTTP APIs."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Application error that serialises to an RFC 9457 problem document."""

    def __init__(
        self,
        *,
        type_: str = "about:blank",
        title: str,
        status: int,
        detail: str,
        instance: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.type = type_
        self.title = title
        self.status = status
        self.detail = detail
        self.instance = instance
        self.extensions = extensions or {}

    def to_problem(self, instance: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
        resolved = instance or self.instance
        if resolved is not None:
            body["instance"] = resolved
        body.update(self.extensions)
        return body


def _problem_response(status: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _problem_response(exc.status, exc.to_problem(instance=str(request.url.path)))

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _problem_response(
            exc.status_code,
            {
                "type": "about:blank",
                "title": detail or "HTTP Error",
                "status": exc.status_code,
                "detail": detail,
                "instance": str(request.url.path),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _problem_response(
            422,
            {
                "type": "about:blank",
                "title": "Validation Error",
                "status": 422,
                "detail": "Request validation failed",
                "instance": str(request.url.path),
                "errors": exc.errors(),
            },
        )
