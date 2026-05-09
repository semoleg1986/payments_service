from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from src.domain.errors import InvariantViolationError
from src.infrastructure.integrations.http.attribution_discount import (
    HttpAttributionDiscountPort,
)
from src.infrastructure.integrations.http.bonus_wallet import HttpBonusWalletPort
from src.infrastructure.integrations.http.course_access_sync import (
    HttpCourseAccessSyncPort,
)
from src.infrastructure.integrations.http.course_catalog import HttpCourseCatalogPort
from src.infrastructure.integrations.http.user_relations import HttpUserRelationsPort
from src.interface.http import observability


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_http_course_catalog_parses_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_urlopen(request, timeout: float = 2.0):  # noqa: ANN001
        return _FakeResponse(
            {
                "course_id": "course-42",
                "price": 1990,
                "currency": "USD",
                "access_ttl_days": 60,
            }
        )

    monkeypatch.setattr(
        "src.infrastructure.integrations.http.course_catalog.urlopen",
        _fake_urlopen,
    )
    adapter = HttpCourseCatalogPort(
        base_url="http://course-service:8001",
        service_token="token",
        timeout_seconds=2.0,
    )

    snapshot = adapter.get_course("course-42")
    assert snapshot is not None
    assert snapshot.course_id == "course-42"
    assert snapshot.price == 1990.0
    assert snapshot.currency == "USD"
    assert snapshot.access_ttl_days == 60


def test_http_course_catalog_returns_none_for_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_urlopen(request, timeout: float = 2.0):  # noqa: ANN001
        raise HTTPError(request.full_url, 404, "not found", hdrs=None, fp=None)

    monkeypatch.setattr(
        "src.infrastructure.integrations.http.course_catalog.urlopen",
        _fake_urlopen,
    )
    adapter = HttpCourseCatalogPort(
        base_url="http://course-service:8001",
        service_token="token",
        timeout_seconds=2.0,
    )

    assert adapter.get_course("missing") is None


def test_http_course_catalog_raises_for_invalid_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_urlopen(request, timeout: float = 2.0):  # noqa: ANN001
        return _FakeResponse({"course_id": "", "price": "bad", "currency": ""})

    monkeypatch.setattr(
        "src.infrastructure.integrations.http.course_catalog.urlopen",
        _fake_urlopen,
    )
    adapter = HttpCourseCatalogPort(
        base_url="http://course-service:8001",
        service_token="token",
        timeout_seconds=2.0,
    )

    with pytest.raises(InvariantViolationError):
        adapter.get_course("broken")


def test_http_user_relations_reads_boolean(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_urlopen(request, timeout: float = 2.0):  # noqa: ANN001
        return _FakeResponse({"has_relation": True})

    monkeypatch.setattr(
        "src.infrastructure.integrations.http.user_relations.urlopen",
        _fake_urlopen,
    )
    adapter = HttpUserRelationsPort(
        base_url="http://users-service:8002",
        service_token="token",
        timeout_seconds=2.0,
    )

    assert adapter.is_parent_of_student("p1", "s1") is True


def test_http_user_relations_raises_on_upstream_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_urlopen(request, timeout: float = 2.0):  # noqa: ANN001
        raise HTTPError(request.full_url, 500, "server error", hdrs=None, fp=None)

    monkeypatch.setattr(
        "src.infrastructure.integrations.http.user_relations.urlopen",
        _fake_urlopen,
    )
    adapter = HttpUserRelationsPort(
        base_url="http://users-service:8002",
        service_token="token",
        timeout_seconds=2.0,
    )

    with pytest.raises(InvariantViolationError):
        adapter.is_parent_of_student("p1", "s1")


def test_http_attribution_discount_returns_zero_without_token() -> None:
    adapter = HttpAttributionDiscountPort(
        base_url="http://attr-service:8000",
        service_token="token",
        timeout_seconds=2.0,
    )
    result = adapter.resolve_discount(
        attribution_token=None,
        course_id="course-1",
        parent_id="parent-1",
    )
    assert result.kind == "fixed"
    assert result.value == 0.0


def test_http_attribution_discount_parses_valid_discount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_urlopen(request, timeout: float = 2.0):  # noqa: ANN001
        return _FakeResponse(
            {
                "valid": True,
                "discount_type": "percent",
                "discount_value": 15,
                "discount": {"amount": 15, "currency": "USD"},
            }
        )

    monkeypatch.setattr(
        "src.infrastructure.integrations.http.attribution_discount.urlopen",
        _fake_urlopen,
    )
    adapter = HttpAttributionDiscountPort(
        base_url="http://attr-service:8000",
        service_token="token",
        timeout_seconds=2.0,
    )

    result = adapter.resolve_discount(
        attribution_token="promo-15",
        course_id="course-1",
        parent_id="parent-1",
    )
    assert result.kind == "percent"
    assert result.value == 15.0


def test_http_attribution_discount_returns_zero_for_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_urlopen(request, timeout: float = 2.0):  # noqa: ANN001
        return _FakeResponse(
            {
                "valid": False,
                "discount": {"amount": 0, "currency": "USD"},
            }
        )

    monkeypatch.setattr(
        "src.infrastructure.integrations.http.attribution_discount.urlopen",
        _fake_urlopen,
    )
    adapter = HttpAttributionDiscountPort(
        base_url="http://attr-service:8000",
        service_token="token",
        timeout_seconds=2.0,
    )

    result = adapter.resolve_discount(
        attribution_token="bad-token",
        course_id="course-1",
        parent_id="parent-1",
    )
    assert result.kind == "fixed"
    assert result.value == 0.0


def test_http_course_access_sync_posts_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_urlopen(request, timeout: float = 2.0):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse({})

    monkeypatch.setattr(
        "src.infrastructure.integrations.http.course_access_sync.urlopen",
        _fake_urlopen,
    )
    adapter = HttpCourseAccessSyncPort(
        base_url="http://course-service:8001",
        service_token="sync-token",
        timeout_seconds=2.0,
    )

    adapter.sync_course_access_granted(
        event_id="evt-1",
        course_id="course-1",
        student_id="student-1",
        granted_status="approved",
    )

    assert (
        captured["url"]
        == "http://course-service:8001/internal/v1/access/events/course-access-granted"
    )
    assert captured["headers"]["X-service-token"] == "sync-token"
    assert captured["body"] == {
        "event_id": "evt-1",
        "course_id": "course-1",
        "student_id": "student-1",
        "granted_status": "approved",
    }


def test_http_bonus_wallet_quote_parses_allowed_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_urlopen(request, timeout: float = 2.0):  # noqa: ANN001
        return _FakeResponse(
            {
                "parent_id": "parent-1",
                "requested_amount": 25,
                "available_balance": 40,
                "allowed_amount": 25,
                "payment_intent_id": "pi-1",
            }
        )

    monkeypatch.setattr(
        "src.infrastructure.integrations.http.bonus_wallet.urlopen",
        _fake_urlopen,
    )
    adapter = HttpBonusWalletPort(
        base_url="http://bonus-service:8006",
        service_token="token",
        timeout_seconds=2.0,
    )

    result = adapter.quote_redeem(
        parent_id="parent-1",
        requested_amount=25,
        payment_intent_id="pi-1",
    )
    assert result.requested_amount == 25
    assert result.allowed_amount == 25


def test_http_adapters_forward_correlation_id_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, dict[str, str]] = {}

    def _fake_urlopen(request, timeout: float = 2.0):  # noqa: ANN001
        captured[request.full_url] = dict(request.header_items())
        if request.full_url.endswith("/payment-snapshot"):
            return _FakeResponse(
                {
                    "course_id": "course-42",
                    "price": 1990,
                    "currency": "USD",
                    "access_ttl_days": 60,
                }
            )
        if "/parent-students/" in request.full_url:
            return _FakeResponse({"has_relation": True})
        if request.full_url.endswith("/discount/resolve"):
            return _FakeResponse(
                {
                    "valid": False,
                    "discount": {"amount": 0, "currency": "USD"},
                }
            )
        return _FakeResponse({})

    monkeypatch.setattr(
        "src.infrastructure.integrations.http.course_catalog.urlopen",
        _fake_urlopen,
    )
    monkeypatch.setattr(
        "src.infrastructure.integrations.http.user_relations.urlopen",
        _fake_urlopen,
    )
    monkeypatch.setattr(
        "src.infrastructure.integrations.http.attribution_discount.urlopen",
        _fake_urlopen,
    )
    monkeypatch.setattr(
        "src.infrastructure.integrations.http.course_access_sync.urlopen",
        _fake_urlopen,
    )

    request_token = observability._CURRENT_REQUEST_ID.set("req-001")
    correlation_token = observability._CURRENT_CORRELATION_ID.set("corr-001")
    try:
        HttpCourseCatalogPort(
            base_url="http://course-service:8001",
            service_token="token",
            timeout_seconds=2.0,
        ).get_course("course-42")
        HttpUserRelationsPort(
            base_url="http://users-service:8002",
            service_token="token",
            timeout_seconds=2.0,
        ).is_parent_of_student("p1", "s1")
        HttpAttributionDiscountPort(
            base_url="http://attr-service:8000",
            service_token="token",
            timeout_seconds=2.0,
        ).resolve_discount(
            attribution_token="promo-15",
            course_id="course-1",
            parent_id="parent-1",
        )
        HttpCourseAccessSyncPort(
            base_url="http://course-service:8001",
            service_token="sync-token",
            timeout_seconds=2.0,
        ).sync_course_access_granted(
            event_id="evt-1",
            course_id="course-1",
            student_id="student-1",
            granted_status="approved",
        )
    finally:
        observability._CURRENT_REQUEST_ID.reset(request_token)
        observability._CURRENT_CORRELATION_ID.reset(correlation_token)

    assert observability.current_correlation_id() is None
    for headers in captured.values():
        assert headers["X-correlation-id"] == "corr-001"
