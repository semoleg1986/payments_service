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

- `POST /v1/parent/payments/intents`
  - поддерживает явный `idempotency_key`
  - повтор с тем же `(parent_id, idempotency_key)` возвращает существующий intent
- `POST /v1/admin/payments/{payment_intent_id}/approve`
  - защищен natural-key инвариантом active-доступа по `(course_id, student_id)`
  - повтор не должен создавать второй `CourseAccessGrant`
  - но не гарантирует повторение исходного HTTP-ответа один в один
- исходящее событие `course.access.granted`
  - публикуется с детерминированным `event_id`
  - предназначено для replay-safe потребителя (`course_service`)
