from __future__ import annotations

from types import SimpleNamespace

from src.interface.http import main


def test_dispatch_outbox_cli_invokes_facade(monkeypatch) -> None:
    calls: list[int] = []

    class _Facade:
        def dispatch_pending_side_effects(self, *, limit: int = 100) -> None:
            calls.append(limit)

    monkeypatch.setattr(
        main,
        "build_runtime",
        lambda: SimpleNamespace(facade=_Facade()),
    )

    exit_code = main.main(["dispatch-outbox", "--limit", "17"])

    assert exit_code == 0
    assert calls == [17]
