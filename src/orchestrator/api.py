"""FastAPI surface for orchestrating asynchronous runs."""
from __future__ import annotations

from .api_app import create_app

app = create_app()

__all__ = ["app", "create_app"]
