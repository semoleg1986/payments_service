# payments_service

Сервис ручной оплаты родителем и выдачи доступа к курсу после подтверждения админом.

## Быстрый старт

```bash
cp .env.example .env
docker compose up -d --build
```

Проверка:

```bash
curl -fsS http://127.0.0.1:8004/healthz
```

## Миграции

```bash
make migrate
```

Создать новую миграцию:

```bash
make makemigration MSG=add_new_fields
```

## Локальный запуск без Docker

```bash
pip install -r requirements.in
make migrate
make run
```

## Переменные окружения

Ключевые переменные в [.env.example](/Users/olegsemenov/Programming/curs/payments_service/.env.example):

- `PAYMENTS_DATABASE_URL`
- `PAYMENTS_USE_INMEMORY`
- `PAYMENTS_AUTH_JWKS_URL` / `PAYMENTS_AUTH_JWKS_JSON`
- `PAYMENTS_SERVICE_TOKEN`
