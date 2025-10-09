"""Service layer for the asynchronous orchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ("AsyncCallbackManager", "AsyncDBConnector", "AsyncOrchestrator", "RunManager")


def __getattr__(name: str) -> Any:  # pragma: no cover - runtime convenience import
    if name == "AsyncCallbackManager":
        from .callbacks import AsyncCallbackManager as _AsyncCallbackManager

        return _AsyncCallbackManager
    if name == "AsyncDBConnector":
        from ..db.db_connector import AsyncDBConnector as _AsyncDBConnector

        return _AsyncDBConnector
    if name == "AsyncOrchestrator":
        from .workflow import AsyncOrchestrator as _AsyncOrchestrator

        return _AsyncOrchestrator
    if name == "RunManager":
        from .run_manager import RunManager as _RunManager

        return _RunManager
    raise AttributeError(f"module 'services' has no attribute {name!r}")


if TYPE_CHECKING:  # pragma: no cover - imported for type checkers only
    from .callbacks import AsyncCallbackManager as AsyncCallbackManager
    from ..db.db_connector import AsyncDBConnector as AsyncDBConnector
    from .workflow import AsyncOrchestrator as AsyncOrchestrator
    from .run_manager import RunManager as RunManager
