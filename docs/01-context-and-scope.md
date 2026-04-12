# Bounded Context И Границы

## Название Контекста

**Контекст Платежей И Выдачи Доступа**

## Ответственность

Контекст обязан:
1. создавать и хранить `PaymentIntent`
2. рассчитывать итоговую сумму c учетом скидки
3. фиксировать решение администратора (`approve` / `reject`)
4. создавать/обновлять `CourseAccessGrant`
5. отдавать API статусов оплаты и доступа
6. публиковать доменные события оплаты

## Структура Агрегатов

```shell
PaymentIntent (Aggregate Root)
|- Money (Value Object)
|- Discount (Value Object)
`- PaymentStatus (Value Object)

CourseAccessGrant (Aggregate Root)
|- AccessStatus (Value Object)
`- AccessWindow (Value Object)
```

## Внешние Зависимости

Зависит от:
- `auth_service` (валидация actor token)
- `users_service` (валидация parent/student при необходимости)
- `course_service` (валидация course_id и policy доступа)
- `attribution_service` (скидка по токену канала)

Не зависит от:
- UI/transport деталей
- прямого доступа к БД других сервисов

## Явные Границы

Контекст не должен:
- самостоятельно менять учебный контент
- выдавать права админа/роль пользователя
- выполнять онлайн-списание с карты (до внедрения эквайринга)
