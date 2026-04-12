"""Интеграционный тест HTTP API payments_service."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.interface.http import wiring
from src.interface.http.app import create_app
from src.interface.http.wiring import get_access_token_verifier


class _FakeVerifier:
    def decode_access(self, access_token: str) -> dict[str, str | list[str]]:
        if access_token == "parent-token":
            return {"sub": "parent-1", "roles": ["parent"]}
        if access_token == "admin-token":
            return {"sub": "admin-1", "roles": ["admin"]}
        raise ValueError("bad token")


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_full_flow_create_approve_and_internal_access_check() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    create_resp = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "course_id": "course-1",
            "idempotency_key": "idem-http-1",
            "attribution_token": "promo10-abc",
        },
    )
    assert create_resp.status_code == 201
    payment_id = create_resp.json()["payment_intent_id"]

    approve_resp = client.post(
        f"/v1/admin/payments/{payment_id}/approve",
        headers=_headers("admin-token"),
        json={},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "active"

    internal_resp = client.get(
        "/internal/v1/access/course-1/student-1",
        headers={"X-Service-Token": "dev-service-token"},
    )
    assert internal_resp.status_code == 200
    assert internal_resp.json()["has_access"] is True
