from __future__ import annotations

from fastapi import APIRouter

from app.core.cache import AppCache

router = APIRouter(tags=["health"])


@router.get("/")
def read_root() -> dict:
    """Health probe. ``status`` reflects DB readiness so a started-but-degraded
    service (failed DB init) is distinguishable from a healthy one."""
    return {
        "status": "ok" if AppCache.db_ready else "degraded",
        "db_ready": AppCache.db_ready,
        "message": "Konstanta API is running",
    }
