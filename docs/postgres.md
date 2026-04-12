# PostgreSQL Профиль Payments Service

## Переменные Окружения

```bash
export PAYMENTS_USE_INMEMORY=0
export PAYMENTS_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/payments_service"
export PAYMENTS_AUTO_CREATE_SCHEMA=0
```

## Миграции

```bash
alembic upgrade head
```

## Проверка Схемы

```bash
psql "postgresql://postgres:postgres@localhost:5432/payments_service" -c "\dt"
```

## Примечание

`AUTO_CREATE_SCHEMA` использовать только локально как fallback.
Для stage/prod — только Alembic migrations.
