"""Интеграционный тест HTTP API payments_service."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.interface.http import wiring
from src.interface.http.app import create_app
from src.interface.http.common.rate_limit import reset_rate_limiter
from src.interface.http.observability import reset_metrics
from src.interface.http.wiring import get_access_token_verifier


class _FakeVerifier:
    def decode_access(self, access_token: str) -> dict[str, str | list[str]]:
        if access_token == "parent-token":
            return {
                "sub": "account-parent-1",
                "user_id": "parent-1",
                "roles": ["parent"],
            }
        if access_token == "admin-token":
            return {"sub": "admin-1", "user_id": "admin-1", "roles": ["admin"]}
        raise ValueError("bad token")


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_full_flow_create_approve_and_internal_access_check() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    reset_rate_limiter()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    create_resp = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-1-standard",
            "idempotency_key": "idem-http-1",
            "attribution_token": "promo10-abc",
            "bonus_amount": 15,
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.headers.get("X-Request-ID")
    assert create_resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert create_resp.headers.get("X-Frame-Options") == "DENY"
    assert create_resp.headers.get("Referrer-Policy") == "no-referrer"
    assert (
        create_resp.headers.get("Permissions-Policy")
        == "camera=(), microphone=(), geolocation=()"
    )
    payment_id = create_resp.json()["payment_intent_id"]
    assert create_resp.json()["offer_id"] == "course-1-standard"
    assert create_resp.json()["course_id"] == "course-1"
    assert create_resp.json()["bonus_amount"] == 15
    assert create_resp.json()["final_price"] == 93.0

    approve_resp = client.post(
        f"/v1/admin/payments/{payment_id}/approve",
        headers=_headers("admin-token"),
        json={},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["offer_id"] == "course-1-standard"
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
    reset_rate_limiter()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    resp = client.post(
        "/v1/parent/payments/intents",
        headers={
            **_headers("parent-token"),
            "X-Request-ID": "req-fixed-001",
            "X-Correlation-ID": "corr-fixed-001",
        },
        json={"parent_id": "parent-1"},
    )
    assert resp.status_code == 422
    assert resp.headers.get("content-type") == "application/problem+json"
    assert resp.headers.get("X-Request-ID") == "req-fixed-001"
    assert resp.headers.get("X-Correlation-ID") == "corr-fixed-001"
    assert resp.json().get("type") == "https://api.example.com/problems/validation"
    assert resp.json().get("status") == 422
    assert resp.json().get("request_id") == "req-fixed-001"
    assert resp.json().get("correlation_id") == "corr-fixed-001"


def test_http_exception_is_returned_as_problem_json() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    reset_rate_limiter()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    resp = client.get(
        "/internal/v1/access/course-1/student-1",
        headers={
            "X-Service-Token": "wrong-token",
            "X-Request-ID": "req-fixed-http-001",
            "X-Correlation-ID": "corr-fixed-http-001",
        },
    )

    assert resp.status_code == 401
    assert resp.headers.get("content-type") == "application/problem+json"
    assert resp.headers.get("X-Request-ID") == "req-fixed-http-001"
    assert resp.headers.get("X-Correlation-ID") == "corr-fixed-http-001"
    assert resp.json().get("type") == "https://api.example.com/problems/unauthorized"
    assert resp.json().get("status") == 401
    assert resp.json().get("request_id") == "req-fixed-http-001"
    assert resp.json().get("correlation_id") == "corr-fixed-http-001"


def test_admin_can_list_and_get_payment_intents() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    reset_rate_limiter()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    create_resp = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-1-standard",
            "idempotency_key": "idem-http-admin-list-1",
        },
    )
    assert create_resp.status_code == 201
    payment_id = create_resp.json()["payment_intent_id"]

    list_resp = client.get(
        "/v1/admin/payments",
        headers=_headers("admin-token"),
        params={"status": "pending", "limit": 10, "offset": 0},
    )
    assert list_resp.status_code == 200
    assert any(item["payment_intent_id"] == payment_id for item in list_resp.json())

    get_resp = client.get(
        f"/v1/admin/payments/{payment_id}",
        headers=_headers("admin-token"),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["payment_intent_id"] == payment_id


def test_parent_can_get_checkout_state() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    reset_rate_limiter()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    create_resp = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-1-standard",
            "idempotency_key": "idem-http-checkout-state-1",
        },
    )
    assert create_resp.status_code == 201
    payment_id = create_resp.json()["payment_intent_id"]

    pending_resp = client.get(
        "/v1/parent/payments/students/student-1/courses/course-1/checkout-state",
        headers=_headers("parent-token"),
    )
    assert pending_resp.status_code == 200
    assert pending_resp.json()["checkout_state"] == "pending_payment"
    assert pending_resp.json()["selected_offer"]["offer_id"] == "course-1-standard"
    assert pending_resp.json()["purchased_offer"] is None
    assert (
        pending_resp.json()["latest_payment_intent"]["payment_intent_id"] == payment_id
    )
    assert pending_resp.json()["access_grant"] is None
    assert (
        pending_resp.json()["available_actions"]["next_action"] == "wait_for_approval"
    )

    approve_resp = client.post(
        f"/v1/admin/payments/{payment_id}/approve",
        headers=_headers("admin-token"),
        json={},
    )
    assert approve_resp.status_code == 200

    access_resp = client.get(
        "/v1/parent/payments/students/student-1/courses/course-1/checkout-state",
        headers=_headers("parent-token"),
    )
    assert access_resp.status_code == 200
    assert access_resp.json()["checkout_state"] == "access_granted"
    assert access_resp.json()["selected_offer"]["offer_id"] == "course-1-standard"
    assert access_resp.json()["purchased_offer"]["offer_id"] == "course-1-standard"
    assert access_resp.json()["access_grant"]["status"] == "active"
    assert access_resp.json()["available_actions"]["next_action"] == "view_access"


def test_admin_can_reject_payment_intent_with_enum_reason() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    reset_rate_limiter()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    create_resp = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-1-standard",
            "idempotency_key": "idem-http-reject-1",
        },
    )
    assert create_resp.status_code == 201
    payment_id = create_resp.json()["payment_intent_id"]

    reject_resp = client.post(
        f"/v1/admin/payments/{payment_id}/reject",
        headers=_headers("admin-token"),
        json={"reason": "stale_pending_intent"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"
    assert reject_resp.json()["rejected_reason"] == "stale_pending_intent"
    assert reject_resp.json()["review_state"] == "rejected"


def test_create_auto_rejects_older_pending_intent_for_same_checkout_context() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    reset_rate_limiter()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    first_resp = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-1-standard",
            "idempotency_key": "idem-http-auto-stale-1",
        },
    )
    assert first_resp.status_code == 201
    first_id = first_resp.json()["payment_intent_id"]

    second_resp = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-1-standard",
            "idempotency_key": "idem-http-auto-stale-2",
        },
    )
    assert second_resp.status_code == 201

    first_get = client.get(
        f"/v1/admin/payments/{first_id}",
        headers=_headers("admin-token"),
    )
    assert first_get.status_code == 200
    assert first_get.json()["status"] == "rejected"
    assert first_get.json()["rejected_reason"] == "stale_pending_intent"


def test_metrics_endpoint_exposes_prometheus_metrics() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    reset_rate_limiter()
    app = create_app()
    client = TestClient(app)

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text
    assert "http_errors_total" in response.text
    assert 'outbox_pending_total{service="payments_service"} 0' in response.text
    assert (
        'outbox_oldest_pending_age_seconds{service="payments_service"} 0.0'
        in response.text
    )


def test_denied_admin_http_attempt_is_retained_as_audit_evidence() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    reset_rate_limiter()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    create_resp = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-1-standard",
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


def test_parent_create_payment_intent_is_rate_limited(monkeypatch) -> None:
    monkeypatch.setenv("PAYMENTS_RATE_LIMIT_PARENT_CREATE_MAX", "1")
    monkeypatch.setenv("PAYMENTS_RATE_LIMIT_PARENT_CREATE_WINDOW_SECONDS", "60")
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    reset_rate_limiter()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    first_resp = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-1-standard",
            "idempotency_key": "idem-http-rl-parent-1",
        },
    )
    assert first_resp.status_code == 201

    limited_resp = client.post(
        "/v1/parent/payments/intents",
        headers={
            **_headers("parent-token"),
            "X-Request-ID": "req-payments-rl-parent-1",
            "X-Correlation-ID": "corr-payments-rl-parent-1",
        },
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-2-standard",
            "idempotency_key": "idem-http-rl-parent-2",
        },
    )
    assert limited_resp.status_code == 429
    assert (
        limited_resp.json()["detail"]["detail"]
        == "Слишком много запросов, попробуйте позже."
    )
    assert limited_resp.json()["detail"]["request_id"] == "req-payments-rl-parent-1"
    assert (
        limited_resp.json()["detail"]["correlation_id"] == "corr-payments-rl-parent-1"
    )


def test_bonus_amount_is_replayed_by_payment_intent_idempotency() -> None:
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    reset_rate_limiter()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    first_resp = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-1-standard",
            "idempotency_key": "idem-http-bonus-1",
            "bonus_amount": 20,
        },
    )
    assert first_resp.status_code == 201

    replay_resp = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-1-standard",
            "idempotency_key": "idem-http-bonus-1",
            "bonus_amount": 20,
        },
    )
    assert replay_resp.status_code == 201
    assert (
        replay_resp.json()["payment_intent_id"]
        == first_resp.json()["payment_intent_id"]
    )
    assert replay_resp.json()["bonus_amount"] == 20


def test_admin_approve_payment_intent_is_rate_limited(monkeypatch) -> None:
    monkeypatch.setenv("PAYMENTS_RATE_LIMIT_ADMIN_APPROVE_MAX", "1")
    monkeypatch.setenv("PAYMENTS_RATE_LIMIT_ADMIN_APPROVE_WINDOW_SECONDS", "60")
    wiring._runtime = None  # type: ignore[attr-defined]
    reset_metrics()
    reset_rate_limiter()
    app = create_app()
    app.dependency_overrides[get_access_token_verifier] = lambda: _FakeVerifier()
    client = TestClient(app)

    first_create = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-1",
            "offer_id": "course-1-standard",
            "idempotency_key": "idem-http-rl-approve-1",
        },
    )
    second_create = client.post(
        "/v1/parent/payments/intents",
        headers=_headers("parent-token"),
        json={
            "parent_id": "parent-1",
            "student_id": "student-2",
            "offer_id": "course-2-standard",
            "idempotency_key": "idem-http-rl-approve-2",
        },
    )
    assert first_create.status_code == 201
    assert second_create.status_code == 201

    first_payment_id = first_create.json()["payment_intent_id"]
    second_payment_id = second_create.json()["payment_intent_id"]

    first_approve = client.post(
        f"/v1/admin/payments/{first_payment_id}/approve",
        headers=_headers("admin-token"),
        json={},
    )
    assert first_approve.status_code == 200

    limited_resp = client.post(
        f"/v1/admin/payments/{second_payment_id}/approve",
        headers={
            **_headers("admin-token"),
            "X-Request-ID": "req-payments-rl-approve-1",
            "X-Correlation-ID": "corr-payments-rl-approve-1",
        },
        json={},
    )
    assert limited_resp.status_code == 429
    assert (
        limited_resp.json()["detail"]["detail"]
        == "Слишком много запросов, попробуйте позже."
    )
    assert limited_resp.json()["detail"]["request_id"] == "req-payments-rl-approve-1"
    assert (
        limited_resp.json()["detail"]["correlation_id"] == "corr-payments-rl-approve-1"
    )
