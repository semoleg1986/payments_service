"""Интеграционный тест HTTP API payments_service."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.interface.http import wiring
from src.interface.http.app import create_app
from src.interface.http.observability import reset_metrics
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
    reset_metrics()
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
    assert create_resp.headers.get("X-Request-ID")
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

    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    assert 'payment_intents_created_total{result="success"} 1' in metrics_resp.text
    assert (
        'payment_intents_approved_total{access_status="active",result="success"} 1'
        in metrics_resp.text
    )
    assert (
        'payment_access_checks_total{access_status="active",result="granted"} 1'
        in metrics_resp.text
    )

    runtime = wiring.get_runtime()
    assert runtime.facade.course_access_sync is not None


def test_request_id_is_returned_in_error_response() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    resp = client.post(
        "/v1/parent/payments/intents",
        headers={
            **_headers("parent-token"),
            "X-Request-ID": "req-fixed-001",
        },
        json={"parent_id": "parent-1"},
    )
    assert resp.status_code == 422
    assert resp.headers.get("X-Request-ID") == "req-fixed-001"
    assert resp.json().get("request_id") == "req-fixed-001"


def test_metrics_endpoint_exposes_prometheus_metrics() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    app = create_app()
    client = TestClient(app)

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text
    assert "http_errors_total" in response.text


def test_denied_admin_http_attempt_is_retained_as_audit_evidence() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
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
            "idempotency_key": "idem-http-denied-1",
        },
    )
    assert create_resp.status_code == 201
    payment_id = create_resp.json()["payment_intent_id"]

    deny_resp = client.post(
        f"/v1/admin/payments/{payment_id}/approve",
        headers={
            **_headers("parent-token"),
            "X-Request-ID": "req-http-denied-approve-1",
            "X-Correlation-ID": "corr-http-denied-approve-1",
        },
        json={},
    )
    assert deny_resp.status_code == 403

    runtime = wiring.get_runtime()
    records = runtime.audit_repo.list_all()
    assert len(records) == 1
    assert records[0].action == "payment_intent.approve"
    assert records[0].result == "denied"
    assert records[0].request_id == "req-http-denied-approve-1"
    assert records[0].correlation_id == "corr-http-denied-approve-1"
    assert records[0].payment_intent_id == payment_id
