# Ubiquitous Language

- `PaymentIntent` — заявка родителя на оплату курса.
- `PaymentStatus` — состояние заявки: `pending`, `approved`, `rejected`, `expired`, `cancelled`.
- `PaymentDecision` — решение администратора по заявке.
- `CourseAccessGrant` — факт предоставления доступа к курсу.
- `AccessStatus` — состояние доступа: `pending`, `active`, `revoked`, `expired`.
- `AccessWindow` — период действия доступа (start/end).
- `BasePrice` — базовая цена курса.
- `Discount` — скидка по каналу/токену.
- `FinalPrice` — цена к оплате после скидки.
- `AttributionToken` — токен источника/канала.
- `IdempotencyKey` — ключ защиты от повторного создания одной и той же заявки.
- `AuditTrail` — история изменений агрегата (actor, time, action).
