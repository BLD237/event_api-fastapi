from __future__ import annotations

from typing import Any, Optional, TypeVar, Generic

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    status: str
    message: Optional[str] = None
    data: Optional[T] = None


def success_response(
    *, message: Optional[str] = None, data: Optional[T] = None
) -> ApiResponse[T]:
    return ApiResponse(
        status="success",
        message=message,
        data=data,
    )


def error_response(
    *, message: str, data: Optional[T] = None
) -> ApiResponse[T]:
    return ApiResponse(
        status="error",
        message=message,
        data=data,
    )
