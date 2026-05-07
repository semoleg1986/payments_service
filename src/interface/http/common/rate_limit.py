"""Простой in-memory rate limiter для payments HTTP endpoints."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request

from src.infrastructure.config.settings import Settings
from src.interface.http.common.actor import HttpActor, get_http_actor
from src.interface.http.observability import increment_counter
from src.interface.http.wiring import get_settings


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    """Правило rate-limit: не больше `max_requests` за `window_seconds`."""

    max_requests: int
    window_seconds: int


class InMemoryRateLimiter:
    """Потокобезопасный sliding-window limiter."""

    def __init__(self, now: Callable[[], float] | None = None) -> None:
        self._now = now or time.monotonic
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, scope: str, key: str, rule: RateLimitRule) -> bool:
        """Проверяет и учитывает запрос."""

        now = self._now()
        boundary = now - float(rule.window_seconds)
        token = (scope, key)

        with self._lock:
            bucket = self._events[token]
            while bucket and bucket[0] <= boundary:
                bucket.popleft()
            if len(bucket) >= rule.max_requests:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        """Очищает состояние limiter (для тестов)."""

        with self._lock:
            self._events.clear()


_limiter = InMemoryRateLimiter()


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _correlation_id(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None)


def enforce_rate_limit(
    *,
    scope: str,
    key: str,
    rule: RateLimitRule,
    request: Request,
) -> None:
    """Бросает 429, если лимит превышен."""

    if _limiter.allow(scope=scope, key=key, rule=rule):
        return
    increment_counter(
        "payments_rate_limit_hits_total",
        "Total payments endpoint rate-limit hits.",
        scope=scope,
    )
    raise HTTPException(
        status_code=429,
        detail={
            "type": "https://api.example.com/problems/rate-limit",
            "title": "Слишком много запросов",
            "status": 429,
            "detail": "Слишком много запросов, попробуйте позже.",
            "instance": str(request.url.path),
            "request_id": _request_id(request),
            "correlation_id": _correlation_id(request),
        },
    )


def _parent_create_rule(settings: Settings) -> RateLimitRule:
    return RateLimitRule(
        max_requests=settings.parent_payment_create_rate_limit_max,
        window_seconds=settings.parent_payment_create_rate_limit_window_seconds,
    )


def _admin_approve_rule(settings: Settings) -> RateLimitRule:
    return RateLimitRule(
        max_requests=settings.admin_payment_approve_rate_limit_max,
        window_seconds=settings.admin_payment_approve_rate_limit_window_seconds,
    )


def enforce_parent_create_rate_limit(
    request: Request,
    actor: HttpActor = Depends(get_http_actor),
    settings: Settings = Depends(get_settings),
) -> None:
    """Rate-limit для parent create-intent."""

    enforce_rate_limit(
        scope="parent_create_intent",
        key=actor.actor_id,
        rule=_parent_create_rule(settings),
        request=request,
    )


def enforce_admin_approve_rate_limit(
    request: Request,
    actor: HttpActor = Depends(get_http_actor),
    settings: Settings = Depends(get_settings),
) -> None:
    """Rate-limit для admin approve-intent."""

    enforce_rate_limit(
        scope="admin_approve_intent",
        key=actor.actor_id,
        rule=_admin_approve_rule(settings),
        request=request,
    )


def reset_rate_limiter() -> None:
    """Сбрасывает глобальный limiter."""

    _limiter.reset()
