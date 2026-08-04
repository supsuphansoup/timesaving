"""
Standard response wrappers.

Uses orjson for serialisation so that datetime, UUID, Enum, etc.
are automatically converted to JSON without manual encoding.
"""

from typing import Any

from fastapi.responses import ORJSONResponse


def success_response(
    data: Any = None,
    message: str = "SUCCESS",
    status_code: int = 200,
) -> ORJSONResponse:
    """Return the standard success response wrapper."""
    return ORJSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "status_code": status_code,
            "message": message,
            "data": data,
        },
    )


def error_response(
    message: str,
    error_code: str,
    status_code: int = 400,
) -> ORJSONResponse:
    """Return the standard error response wrapper."""
    return ORJSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "status_code": status_code,
            "error_code": error_code,
            "message": message,
        },
    )
