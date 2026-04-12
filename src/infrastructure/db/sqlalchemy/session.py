"""Фабрика SQLAlchemy-сессий."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def build_engine(url: str) -> Engine:
    """Создает SQLAlchemy engine."""

    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(
        url, future=True, pool_pre_ping=True, connect_args=connect_args
    )


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Создает sessionmaker."""

    return sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
