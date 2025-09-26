"""Security utilities for API key authentication."""
from __future__ import annotations

import os
from typing import Callable

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param

# API Key Security
API_KEY = os.getenv("API_KEY", "your-secret-api-key")
security = HTTPBearer()

# Paths that don't require authentication
EXEMPT_PATHS = {"/", "/docs", "/openapi.json", "/redoc", "/health"}


async def verify_api_key(request: Request) -> None:
    """Verify API key from request headers."""
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    scheme, credentials = get_authorization_scheme_param(authorization)
    if scheme.lower() != "bearer" or credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_api_key_middleware() -> Callable:
    """Create middleware function for API key verification."""
    async def api_key_middleware(request: Request, call_next):
        """Middleware to verify API key for all requests."""
        # Skip API key verification for exempt paths
        if request.url.path in EXEMPT_PATHS:
            response = await call_next(request)
            return response
            
        try:
            await verify_api_key(request)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": exc.detail}
            )
        
        response = await call_next(request)
        return response
    
    return api_key_middleware