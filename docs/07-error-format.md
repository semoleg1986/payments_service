# Error Format

Сервис использует RFC7807 (`application/problem+json`).

## Базовые Поля

- `type`
- `title`
- `status`
- `detail`
- `instance`
- `request_id`
- `correlation_id`

`X-Request-ID` и `X-Correlation-ID` также возвращаются в headers, когда доступны.

## Типовые Ошибки

- `validation_error` (`422`)
- `unauthorized` (`401`)
- `access_denied` (`403`)
- `not_found` (`404`)
- `conflict` (`409`)
- `invariant_violation` (`400`)
- `internal_error` (`500`)

## Пример

```json
{
  "type": "https://api.example.com/problems/invariant-violation",
  "title": "Нарушение бизнес-инварианта",
  "status": 400,
  "detail": "PaymentIntent уже подтвержден.",
  "instance": "/v1/admin/payments/pi_123/approve",
  "request_id": "req-123",
  "correlation_id": "corr-123"
}
```
