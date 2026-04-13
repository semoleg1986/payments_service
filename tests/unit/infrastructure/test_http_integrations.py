from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from src.domain.errors import InvariantViolationError
from src.infrastructure.integrations.http.course_catalog import HttpCourseCatalogPort
from src.infrastructure.integrations.http.user_relations import HttpUserRelationsPort


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

