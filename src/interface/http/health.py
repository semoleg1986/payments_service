"""Health endpoint-ы."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness/readiness для контейнера."""

    return {"status": "ok"}
