# Infrastructure Слой

## Назначение

Infrastructure реализует порты application/domain:
- persistence (SQLAlchemy/Postgres)
- transport adapters внешних сервисов
- clock/id генерация
- auth verifier/service token verifier

## Компоненты

- `db/sqlalchemy`:
  - ORM-модели `payment_intents`, `course_access_grants`
  - repository реализации
  - `UnitOfWork`
- `integrations`:
  - `course_service` adapter
  - `users_service` adapter
  - `attribution_service` adapter
- `auth`:
  - JWT/JWKS verifier
  - internal service-token guard

## Конфигурация

- `PAYMENTS_DATABASE_URL`
- `PAYMENTS_USE_INMEMORY`
- `PAYMENTS_AUTO_CREATE_SCHEMA` (временно)
- `PAYMENTS_AUTH_JWKS_URL`
- `PAYMENTS_SERVICE_TOKEN`

## Миграции

- Alembic как единственный способ управления схемой.
- В deployment: `alembic upgrade head`.
