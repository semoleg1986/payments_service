"""Получение actor-контекста из HTTP-запроса."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from src.application.contracts import AccessTokenVerifier
from src.interface.http.wiring import get_access_token_verifier


@dataclass(frozen=True, slots=True)
class HttpActor:
    """Актор, извлеченный из access token."""

    actor_id: str
    roles: tuple[str, ...]


def get_http_actor(
    authorization: str | None = Header(default=None, alias="Authorization"),
    verifier: AccessTokenVerifier = Depends(get_access_token_verifier),
) -> HttpActor:
    """Извлекает actor context из Bearer access token."""

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется Bearer токен.",
        )
    access_token = authorization.removeprefix("Bearer ").strip()
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный Bearer токен.",
        )
    try:
        claims = verifier.decode_access(access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный access token.",
        ) from exc
    actor_id = str(claims.get("sub", "")).strip()
    roles_value = claims.get("roles", [])
    roles = tuple(
        str(item).strip().lower() for item in roles_value if str(item).strip()
    )
    if not actor_id or not roles:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token не содержит обязательные claims.",
        )
    return HttpActor(actor_id=actor_id, roles=roles)
