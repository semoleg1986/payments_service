# Application Layer

## Назначение

Application-слой оркестрирует use-cases платежей и выдачи доступа через порты, не зная деталей HTTP/ORM.

## Команды

- `CreatePaymentIntentCommand`
- `ApprovePaymentIntentCommand`
- `RejectPaymentIntentCommand`
- `CancelPaymentIntentCommand`

## Запросы

- `GetPaymentIntentQuery`
- `GetCourseAccessGrantQuery`
- `ListPaymentsByParentQuery`

## Порты

- `PaymentIntentRepository`
- `CourseAccessGrantRepository`
- `UnitOfWork`
- `Clock`
- `IdGenerator`
- `CourseCatalogPort` (проверка курса/цены)
- `UserRelationsPort` (проверка parent->student)
- `AttributionDiscountPort` (разрешение скидки)

## Facade

`ApplicationFacade` — единый вход в команды/запросы из interface-слоя.
