# Interface Слой

## Назначение

Interface-слой публикует HTTP/gRPC контракты и делегирует бизнес-логику в `ApplicationFacade`.

## Структура

```shell
src/interface/http/
|- app.py
|- main.py
|- health.py
|- errors.py
|- problem_types.py
|- wiring.py
`- v1/
   |- parent/router.py
   |- admin/router.py
   |- internal/router.py
   `- schemas/
      |- payment.py
      `- access.py
```

## Основные Endpoint-ы (MVP)

- `POST /v1/parent/payments/intents`
- `GET /v1/parent/payments/{payment_intent_id}`
- `POST /v1/admin/payments/{payment_intent_id}/approve`
- `POST /v1/admin/payments/{payment_intent_id}/reject`
- `GET /internal/v1/access/{course_id}/{student_id}`

## Правила Границ

- без прямого доступа к БД
- без доменной логики в routers
- единый формат ошибок RFC7807
