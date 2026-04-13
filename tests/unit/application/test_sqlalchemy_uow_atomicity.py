"""Тест атомарности SQL транзакции approve use-case."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.contracts.commands import (
    ApprovePaymentIntentCommand,
    CreatePaymentIntentCommand,
)
from src.application.services.facade import PaymentApplicationFacade
from src.infrastructure.db.sqlalchemy import models as _models  # noqa: F401
from src.infrastructure.db.sqlalchemy.base import Base
from src.infrastructure.db.sqlalchemy.course_access_grant_repository_sqlalchemy import (
    SqlAlchemyCourseAccessGrantRepository,
)
from src.infrastructure.db.sqlalchemy.payment_intent_repository_sqlalchemy import (
    SqlAlchemyPaymentIntentRepository,
)
from src.infrastructure.db.sqlalchemy.session import build_engine, build_session_factory
from src.infrastructure.db.sqlalchemy.uow import SqlAlchemyUnitOfWork
from src.infrastructure.integrations.in_memory.attribution_discount import (
    InMemoryAttributionDiscountPort,
)
from src.infrastructure.integrations.in_memory.course_catalog import (
    InMemoryCourseCatalogPort,
)
from src.infrastructure.integrations.in_memory.user_relations import (
    InMemoryUserRelationsPort,
)
from src.infrastructure.system.clock import UtcClock
from src.infrastructure.system.id_generator import UuidGenerator


class _FailingAccessRepo(SqlAlchemyCourseAccessGrantRepository):
    """Репозиторий, который падает при сохранении доступа."""

    def save(self, access_grant):  # type: ignore[no-untyped-def]
        super().save(access_grant)
        raise RuntimeError("forced failure after access save")


def test_approve_is_atomic_with_sqlalchemy_uow(tmp_path: Path) -> None:
    db_path = tmp_path / "payments_atomicity.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    session_factory = build_session_factory(engine)

    payment_repo = SqlAlchemyPaymentIntentRepository(session_factory)
    access_repo_ok = SqlAlchemyCourseAccessGrantRepository(session_factory)
    facade_ok = PaymentApplicationFacade(
        payment_repo=payment_repo,
        access_repo=access_repo_ok,
        course_catalog=InMemoryCourseCatalogPort(),
        user_relations=InMemoryUserRelationsPort(),
        attribution=InMemoryAttributionDiscountPort(),
        id_generator=UuidGenerator(),
        clock=UtcClock(),
        uow=SqlAlchemyUnitOfWork(session_factory),
    )

    created = facade_ok.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            course_id="course-1",
            attribution_token=None,
            idempotency_key="atomicity-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    facade_failing = PaymentApplicationFacade(
        payment_repo=payment_repo,
        access_repo=_FailingAccessRepo(session_factory),
        course_catalog=InMemoryCourseCatalogPort(),
        user_relations=InMemoryUserRelationsPort(),
        attribution=InMemoryAttributionDiscountPort(),
        id_generator=UuidGenerator(),
        clock=UtcClock(),
        uow=SqlAlchemyUnitOfWork(session_factory),
    )

    with pytest.raises(RuntimeError):
        facade_failing.approve_payment_intent(
            ApprovePaymentIntentCommand(
                payment_intent_id=created.payment_intent_id,
                admin_id="admin-1",
                admin_roles=("admin",),
                access_grant_id="",
            )
        )

    after = payment_repo.get(created.payment_intent_id)
    assert after is not None
    assert after.status.value == "pending"
    assert access_repo_ok.get_by_payment_intent(created.payment_intent_id) is None
