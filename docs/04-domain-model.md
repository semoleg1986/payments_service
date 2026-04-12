# Domain Model

## Aggregate: PaymentIntent

### Идентичность
- `payment_intent_id` (UUID)

### Состояние
- `parent_id`
- `student_id`
- `course_id`
- `status`
- `base_price`
- `discount_type`
- `discount_value`
- `final_price`
- `currency`
- `attribution_token` (nullable)
- `expires_at` (nullable)
- `version`
- `created_at`, `updated_at`
- `created_by`, `updated_by`

### Поведение
- `approve(by_admin_id, at)`
- `reject(by_admin_id, at, reason)`
- `expire(at)`
- `cancel(by_actor_id, at)`

## Aggregate: CourseAccessGrant

### Идентичность
- `access_grant_id` (UUID)

### Состояние
- `payment_intent_id`
- `course_id`
- `student_id`
- `status`
- `granted_at`
- `expires_at` (nullable)
- `revoked_at` (nullable)
- `version`
- `created_at`, `updated_at`
- `created_by`, `updated_by`

### Поведение
- `activate(by_admin_id, at, expires_at?)`
- `revoke(by_admin_id, at, reason)`
- `expire(at)`
