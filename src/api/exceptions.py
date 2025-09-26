"""Exception handlers for the FastAPI application."""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def create_http_exception_handler() -> Callable:
    """Create HTTP exception handler."""
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code}
        )
    return http_exception_handler


def create_validation_exception_handler() -> Callable:
    """Create validation exception handler."""
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request validation errors."""
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Validation error", "details": exc.errors()}
        )
    return validation_exception_handler


def create_general_exception_handler() -> Callable:
    """Create general exception handler."""
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle general exceptions."""
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"}
        )
    return general_exception_handler


def register_exception_handlers(app) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(HTTPException, create_http_exception_handler())
    app.add_exception_handler(RequestValidationError, create_validation_exception_handler())
    app.add_exception_handler(Exception, create_general_exception_handler())