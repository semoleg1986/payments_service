"""DI-композиция payments_service."""

from __future__ import annotations

from dataclasses import dataclass

from src.application.contracts import AccessTokenVerifier
from src.application.services import PaymentApplicationFacade
from src.infrastructure.auth.jwks_access_token_verifier import JwksAccessTokenVerifier
from src.infrastructure.config.settings import Settings
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
from src.infrastructure.integrations.http.course_catalog import HttpCourseCatalogPort
from src.infrastructure.integrations.http.attribution_discount import (
    HttpAttributionDiscountPort,
)
from src.infrastructure.integrations.http.user_relations import HttpUserRelationsPort
from src.infrastructure.integrations.in_memory.course_catalog import (
    InMemoryCourseCatalogPort,
)
from src.infrastructure.integrations.in_memory.user_relations import (
    InMemoryUserRelationsPort,
)
from src.infrastructure.persistence.in_memory.course_access_grant_repository import (
    InMemoryCourseAccessGrantRepository,
)
from src.infrastructure.persistence.in_memory.payment_intent_repository import (
    InMemoryPaymentIntentRepository,
)
from src.infrastructure.system.clock import UtcClock
from src.infrastructure.system.id_generator import UuidGenerator
from src.infrastructure.system.unit_of_work import InMemoryUnitOfWork


@dataclass(slots=True)
class RuntimeContainer:
    """Контейнер runtime-зависимостей сервиса."""

    settings: Settings
    facade: PaymentApplicationFacade
    access_token_verifier: AccessTokenVerifier


def build_runtime() -> RuntimeContainer:
    """Собирает runtime-контейнер."""

    settings = Settings.from_env()
    access_token_verifier = JwksAccessTokenVerifier(
        issuer=settings.auth_issuer,
        audience=settings.auth_audience,
        jwks_url=settings.auth_jwks_url,
        jwks_json=settings.auth_jwks_json,
    )

    if settings.use_inmemory:
        payment_repo = InMemoryPaymentIntentRepository()
        access_repo = InMemoryCourseAccessGrantRepository()
        uow = InMemoryUnitOfWork()
    else:
        from src.infrastructure.db.sqlalchemy import models as _models  # noqa: F401

        engine = build_engine(settings.database_url)
        if settings.auto_create_schema:
            Base.metadata.create_all(bind=engine)
        session_factory = build_session_factory(engine)
        payment_repo = SqlAlchemyPaymentIntentRepository(session_factory)
        access_repo = SqlAlchemyCourseAccessGrantRepository(session_factory)
        uow = SqlAlchemyUnitOfWork(session_factory)

    if settings.integrations_use_inmemory:
        course_catalog = InMemoryCourseCatalogPort()
        user_relations = InMemoryUserRelationsPort()
        attribution = InMemoryAttributionDiscountPort()
    else:
        course_catalog = HttpCourseCatalogPort(
            base_url=settings.course_service_base_url,
            service_token=settings.course_service_token,
            timeout_seconds=settings.course_service_timeout_seconds,
        )
        user_relations = HttpUserRelationsPort(
            base_url=settings.users_service_base_url,
            service_token=settings.users_service_token,
            timeout_seconds=settings.users_service_timeout_seconds,
        )
        attribution = HttpAttributionDiscountPort(
            base_url=settings.attr_service_base_url,
            service_token=settings.attr_service_token,
            timeout_seconds=settings.attr_service_timeout_seconds,
        )

    facade = PaymentApplicationFacade(
        payment_repo=payment_repo,
        access_repo=access_repo,
        course_catalog=course_catalog,
        user_relations=user_relations,
        attribution=attribution,
        id_generator=UuidGenerator(),
        clock=UtcClock(),
        uow=uow,
    )
    return RuntimeContainer(
        settings=settings,
        facade=facade,
        access_token_verifier=access_token_verifier,
    )
