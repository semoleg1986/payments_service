# Акторы И Use Cases

## Акторы

- `parent` — инициирует оплату курса ребенку.
- `admin` — подтверждает/отклоняет оплату и выдачу доступа.
- `internal service` — сервисные вызовы для проверки статуса оплаты/доступа.

## Основные Сценарии

1. `Parent creates payment intent`
- вход: `course_id`, `student_id`, `attribution_token?`
- выход: `payment_intent_id`, сумма, статус `pending`

2. `Admin approves payment`
- вход: `payment_intent_id`
- выход: `PaymentStatus=approved`, `CourseAccessGrant=active`

3. `Admin rejects payment`
- вход: `payment_intent_id`, `reason`
- выход: `PaymentStatus=rejected`, доступ не выдается

4. `Get payment status`
- вход: `payment_intent_id`
- выход: актуальный `PaymentStatus` + данные аудита

5. `Get course access status`
- вход: `course_id`, `student_id`
- выход: `AccessStatus` и окно действия доступа
