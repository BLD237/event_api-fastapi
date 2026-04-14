from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ApiResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[Any] = None


def success_response(
    *, message: Optional[str] = None, data: Optional[Any] = None
) -> ApiResponse:
    return ApiResponse(
        status="success",
        message=message,
        data=data,
    )


def error_response(
    *, message: str, data: Optional[Any] = None
) -> ApiResponse:
    return ApiResponse(
        status="error",
        message=message,
        data=data,
    )
