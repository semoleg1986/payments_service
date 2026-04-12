# Инварианты И Политики

## Инварианты

1. `PaymentIntent` может быть подтвержден только из `pending`.
2. Повторный `approve` на уже `approved` intent запрещен.
3. `CourseAccessGrant` создается только после `PaymentStatus=approved`.
4. Для пары (`course_id`, `student_id`) одновременно может быть только один `active` доступ.
5. `final_price >= 0`, `currency` обязательна.
6. Все state transitions фиксируют `updated_at`, `updated_by`, `version`.

## Политики Доступа

- `parent` может создавать intent только для своего ребенка (проверка через `users_service`).
- `admin` может approve/reject любой `pending` intent.
- internal endpoints защищены сервисным токеном.

## Идемпотентность

- Создание intent поддерживает `IdempotencyKey`.
- Повторный вызов с тем же ключом возвращает существующий intent.

## TTL

- `PaymentIntent` может иметь TTL и переходить в `expired`.
- Доступ к курсу (`AccessGrant`) может иметь TTL (`access_ttl_days`).
