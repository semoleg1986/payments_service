# Integration Contracts

## Входящие Контракты

### Auth
- JWT access token (`iss=auth_service`, `aud=platform_clients`, `typ=access`)

### Parent/API
- `CreatePaymentIntent` request
- `GetPaymentIntent` request

### Admin/API
- `ApprovePaymentIntent`
- `RejectPaymentIntent`

## Исходящие Контракты

### users_service
- Проверка соответствия `parent_id -> student_id`
- Проверка существования student/parent

### course_service
- Проверка существования курса
- Получение цены/ограничений курса
- Публикация/синхронизация факта доступа (при необходимости через internal endpoint/event)

### attribution_service
- Разрешение скидки по `attribution_token`
- Подтверждение конверсии после `approve`

## События (outbox)

- `payment.intent.created`
- `payment.intent.approved`
- `payment.intent.rejected`
- `course.access.granted`
- `course.access.revoked`

## Требования К Идемпотентности

- Все команды изменения состояния принимают `idempotency_key` или защищены уникальными доменными ключами.
