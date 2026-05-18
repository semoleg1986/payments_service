# payments_service

Payment intent and course access service.

## Responsibility

`payments_service` owns:
- parent-created payment intents
- admin approval and rejection
- course access grants after approval
- access checks for downstream consumers
- outbox/side-effect dispatch for payment lifecycle

Current model: payment confirmation is still admin-driven.

## Local run

### Install
```bash
make install
```

### Run
```bash
make run
```

### Health
```bash
curl -fsS http://127.0.0.1:8004/healthz
```

## Environment

- [payments_service/.env.example](/Users/olegsemenov/Programming/curs/payments_service/.env.example)
- [payments_service/.env.local.example](/Users/olegsemenov/Programming/curs/payments_service/.env.local.example)

Key variables:
- `PAYMENTS_DATABASE_URL`
- `PAYMENTS_AUTH_JWKS_URL`
- `PAYMENTS_SERVICE_TOKEN`
- `PAYMENTS_COURSE_SERVICE_BASE_URL`
- `PAYMENTS_USERS_SERVICE_BASE_URL`
- `PAYMENTS_ATTR_SERVICE_BASE_URL`
- `PAYMENTS_INTEGRATIONS_USE_INMEMORY`

## Tests and quality

```bash
make test
make test-quick
make lint
make format
```

## Migrations

```bash
make migrate
make makemigration MSG=add_new_fields
```

## Outbox dispatcher

```bash
python -m src.interface.http.main dispatch-outbox --limit 100
```

## Documentation

- [00-vision.md](/Users/olegsemenov/Programming/curs/payments_service/docs/00-vision.md)
- [10-integration-contracts.md](/Users/olegsemenov/Programming/curs/payments_service/docs/10-integration-contracts.md)
- [postgres.md](/Users/olegsemenov/Programming/curs/payments_service/docs/postgres.md)
