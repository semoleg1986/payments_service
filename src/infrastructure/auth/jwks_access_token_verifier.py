"""JWKS верификатор access token."""

from __future__ import annotations

import json
from urllib.request import urlopen

import jwt

from src.domain.errors import AccessDeniedError


class JwksAccessTokenVerifier:
    """Проверяет access token по JWKS и issuer."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        jwks_json: str | None = None,
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._jwks_url = jwks_url
        self._jwks_json = jwks_json
        self._cached_jwks: dict | None = None

    def decode_access(self, access_token: str) -> dict[str, str | list[str]]:
        """Декодирует и валидирует access token."""

        try:
            header = jwt.get_unverified_header(access_token)
            kid = header.get("kid")
            jwk = self._resolve_jwk(kid=kid)
            claims = jwt.decode(
                access_token,
                jwt.PyJWK.from_dict(jwk).key,
                algorithms=["EdDSA"],
                issuer=self._issuer,
                audience=self._audience,
                options={
                    "require": [
                        "iss",
                        "aud",
                        "sub",
                        "jti",
                        "roles",
                        "iat",
                        "exp",
                        "typ",
                    ]
                },
            )
        except Exception as exc:
            raise AccessDeniedError("Некорректный access token.") from exc

        if claims.get("typ") != "access":
            raise AccessDeniedError("Некорректный тип access token.")
        sub = str(claims.get("sub", "")).strip()
        roles = claims.get("roles", [])
        if not sub:
            raise AccessDeniedError("Access token не содержит subject.")
        if not isinstance(roles, list) or not roles:
            raise AccessDeniedError("Access token содержит некорректные roles.")
        return {"sub": sub, "roles": [str(item) for item in roles]}

    def _resolve_jwk(self, *, kid: str | None) -> dict:
        jwks = self._load_jwks()
        keys = jwks.get("keys", [])
        if not keys:
            raise AccessDeniedError("JWKS не содержит ключей.")
        if kid:
            for key in keys:
                if key.get("kid") == kid:
                    return key
            raise AccessDeniedError("Не найден ключ для kid из токена.")
        return keys[0]

    def _load_jwks(self) -> dict:
        if self._cached_jwks is not None:
            return self._cached_jwks

        if self._jwks_json:
            data = json.loads(self._jwks_json)
            self._cached_jwks = data
            return data

        with urlopen(self._jwks_url, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
        self._cached_jwks = data
        return data
