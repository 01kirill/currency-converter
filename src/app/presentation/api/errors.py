from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    ConflictError,
    DomainError,
    InvalidValueError,
    NotFoundError,
    UnavailableError,
)
from app.presentation.api.schemas import ErrorResponse

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    InvalidValueError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    UnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


async def domain_error_handler(request: Request, e: Exception) -> JSONResponse:
    status_code = next(
        (code for error, code in STATUS_BY_ERROR.items() if isinstance(e, error)),
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return JSONResponse(status_code=status_code, content={"detail": str(e)})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    return {code: {"model": ErrorResponse} for code in codes}
