# SuperAdmin API Documentation

Base URL: `/api/v1/superadmin`

All endpoints (except `/login`) require a Bearer token with `is_superadmin=true` claim.

---

## Authentication

### POST `/api/v1/superadmin/login`

Login and receive a JWT token.

**Request Body**

```json
{
  "email": "admin@manahrms.com",
  "password": "your_password"
}
```

**Response `200`**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "admin": {
    "id": 1,
    "email": "admin@manahrms.com",
    "username": "superadmin",
    "full_name": "Super Admin",
    "is_active": true,
    "created_at": "2025-01-01T00:00:00"
  }
}
```

**Error Responses**
| Status | error_code | Description |
|--------|-----------|-------------|
| 401 | `INVALID_CREDENTIALS` | Wrong email or password |
| 403 | `ADMIN_INACTIVE` | Account is deactivated |

---

### GET `/api/v1/superadmin/me`

Get the currently authenticated superadmin's profile.

**Headers:** `Authorization: Bearer <token>`

**Response `200`**

```json
{
  "id": 1,
  "email": "admin@manahrms.com",
  "username": "superadmin",
  "full_name": "Super Admin",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00"
}
```

---

## Dashboard / Stats

### GET `/api/v1/superadmin/stats`

Get a full platform-wide statistics overview.

**Headers:** `Authorization: Bearer <token>`

**Response `200`**

```json
{
  "total_companies": 25,
  "active_companies": 22,
  "inactive_companies": 3,
  "total_subscriptions": 25,
  "active_subscriptions": 18,
  "trial_subscriptions": 4,
  "expired_subscriptions": 2,
  "cancelled_subscriptions": 1,
  "total_employees": 1240,
  "total_revenue_monthly": "45000.00",
  "plans": [
    {
      "id": "uuid-here",
      "name": "Starter",
      "plan_key": "starter",
      "active_subscriptions": 10,
      "is_active": true
    }
  ]
}
```

---

## Company Management

### GET `/api/v1/superadmin/companies`

List all companies with optional filters and pagination.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 50 | Max results (1–500) |
| `search` | string | — | Search by company name or email |
| `is_active` | bool | — | Filter by active/inactive status |

**Response `200`**

```json
[
  {
    "id": 1,
    "company_code": "COMP001",
    "company_name": "Acme Corp",
    "email": "hr@acme.com",
    "phone": "+91-9876543210",
    "company_type": "private",
    "is_active": true,
    "created_at": "2025-03-01T10:00:00",
    "subscription_status": "active",
    "subscription_plan": "Professional",
    "subscription_end": "2026-03-01T10:00:00"
  }
]
```

---

### GET `/api/v1/superadmin/companies/{company_id}`

Get full details of a specific company, including users, employees, and subscription.

**Headers:** `Authorization: Bearer <token>`

**Path Parameter:** `company_id` (int)

**Response `200`**

```json
{
  "id": 1,
  "company_code": "COMP001",
  "company_name": "Acme Corp",
  "email": "hr@acme.com",
  "phone": "+91-9876543210",
  "address": "123 Business Park, Mumbai",
  "company_type": "private",
  "gst_number": "27AABCU9603R1ZX",
  "pan_number": "AABCU9603R",
  "is_active": true,
  "created_at": "2025-03-01T10:00:00",
  "updated_at": "2025-03-15T10:00:00",
  "total_users": 5,
  "total_employees": 80,
  "subscription": {
    "id": "uuid-here",
    "plan_name": "Professional",
    "status": "active",
    "billing_cycle": "monthly",
    "seat_count": 80,
    "billable_seats": 80,
    "price_per_user": "99.00",
    "monthly_cost": "7920.00",
    "current_period_end": "2026-04-01T00:00:00",
    "ai_queries_used": 320,
    "ai_queries_limit": 1000
  }
}
```

**Error:** `404` — Company not found

---

### DELETE `/api/v1/superadmin/companies/{company_id}`

Permanently delete a company and every piece of data linked to it.

**Headers:** `Authorization: Bearer <superadmin-token>`

**Path Parameter:** `company_id` (int)

**What gets deleted**

| Data                               | How                         |
| ---------------------------------- | --------------------------- |
| Employees & user accounts          | DB cascade                  |
| Departments & department access    | DB cascade                  |
| Projects & tasks                   | DB cascade                  |
| Attendance records                 | DB cascade                  |
| Leave types, requests & balances   | DB cascade                  |
| Meetings & events                  | DB cascade                  |
| Chat messages                      | DB cascade                  |
| Subscription, AI usage records     | DB cascade                  |
| Vector store embeddings            | DB cascade                  |
| Employee attachments (metadata)    | DB cascade                  |
| Uploaded files (photos, documents) | Directory deleted from disk |

**Response `200`**

```json
{
  "success": true,
  "message": "Company 'Acme Corp' and all related data permanently deleted."
}
```

**Error:** `404` — Company not found

> **This action is irreversible. There is no soft delete — all data is gone permanently.**

---

### PATCH `/api/v1/superadmin/companies/{company_id}`

Update a company's details or activate/deactivate it.

**Headers:** `Authorization: Bearer <token>`

**Path Parameter:** `company_id` (int)

**Request Body** (all fields optional)

```json
{
  "company_name": "Acme Corporation",
  "phone": "+91-9876543210",
  "address": "456 New Address, Delhi",
  "is_active": false
}
```

**Response `200`**

```json
{
  "success": true,
  "message": "Company deactivated successfully"
}
```

**Error:** `404` — Company not found

---

## Subscription Management

### GET `/api/v1/superadmin/subscriptions`

List all subscriptions across the platform.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 50 | Max results (1–500) |
| `status` | string | — | Filter: `trial`, `active`, `past_due`, `cancelled`, `expired` |
| `plan_key` | string | — | Filter by plan key (e.g. `starter`, `professional`) |

**Response `200`** — Array of subscription objects (see schema below)

---

### GET `/api/v1/superadmin/subscriptions/{company_id}`

Get the subscription for a specific company.

**Headers:** `Authorization: Bearer <token>`

**Response `200` — Subscription Detail Object**

```json
{
  "id": "uuid-here",
  "company_id": 1,
  "company_name": "Acme Corp",
  "plan_name": "Professional",
  "plan_key": "professional",
  "billing_cycle": "monthly",
  "seat_count": 80,
  "billable_seats": 80,
  "price_per_user": "99.00",
  "monthly_cost": "7920.00",
  "status": "active",
  "current_period_start": "2025-03-01T00:00:00",
  "current_period_end": "2025-04-01T00:00:00",
  "trial_end": null,
  "cancel_at_period_end": false,
  "cancelled_at": null,
  "razorpay_subscription_id": "sub_XXXXXX",
  "razorpay_customer_id": "cust_XXXXXX",
  "employees_used": 76,
  "ai_queries_used": 320,
  "ai_queries_limit": 1000,
  "created_at": "2025-03-01T10:00:00",
  "updated_at": "2025-03-15T10:00:00"
}
```

**Error:** `404` — No subscription found for this company

---

### POST `/api/v1/superadmin/subscriptions/{company_id}`

Manually create a subscription for a company that has none.

**Headers:** `Authorization: Bearer <token>`

**Request Body**

```json
{
  "plan_id": "uuid-of-the-plan",
  "billing_cycle": "monthly",
  "seat_count": 10,
  "status": "active",
  "current_period_start": "2025-04-01T00:00:00",
  "current_period_end": "2025-05-01T00:00:00",
  "trial_end": null
}
```

| Field                  | Type                  | Required | Notes                        |
| ---------------------- | --------------------- | -------- | ---------------------------- |
| `plan_id`              | UUID string           | Yes      | Must be a valid plan UUID    |
| `billing_cycle`        | `monthly` \| `yearly` | Yes      |                              |
| `seat_count`           | int ≥ 1               | Yes      |                              |
| `status`               | string                | No       | Default: `active`            |
| `current_period_start` | datetime              | No       | Defaults to now              |
| `current_period_end`   | datetime              | No       | Defaults to +30 or +365 days |
| `trial_end`            | datetime              | No       |                              |

**Response `201`** — Full subscription detail object

**Error Responses**
| Status | Description |
|--------|-------------|
| 400 | Company already has a subscription |
| 400 | Invalid `plan_id` format |
| 404 | Company or plan not found |

---

### PATCH `/api/v1/superadmin/subscriptions/{company_id}/extend`

Extend or set the subscription end date. Reactivates expired subscriptions automatically.

**Headers:** `Authorization: Bearer <token>`

**Request Body** — Provide exactly one of:

```json
{ "days": 30 }
```

```json
{ "new_end_date": "2026-06-01T00:00:00" }
```

| Field          | Type     | Description                    |
| -------------- | -------- | ------------------------------ |
| `days`         | int ≥ 1  | Add N days to current end date |
| `new_end_date` | datetime | Set an absolute end date       |

**Response `200`** — Updated subscription detail object

**Error:** `400` — Neither `days` nor `new_end_date` provided

---

### PATCH `/api/v1/superadmin/subscriptions/{company_id}/change-plan`

Upgrade or downgrade a company's subscription plan.

**Headers:** `Authorization: Bearer <token>`

**Request Body**

```json
{
  "plan_id": "uuid-of-new-plan",
  "billing_cycle": "yearly",
  "reset_period": false
}
```

| Field           | Type                  | Required | Notes                                                            |
| --------------- | --------------------- | -------- | ---------------------------------------------------------------- |
| `plan_id`       | UUID string           | Yes      | The new plan's UUID                                              |
| `billing_cycle` | `monthly` \| `yearly` | Yes      |                                                                  |
| `reset_period`  | bool                  | No       | Default `false`. If `true`, resets `current_period_start` to now |

**Response `200`** — Updated subscription detail object

---

### PATCH `/api/v1/superadmin/subscriptions/{company_id}/change-status`

Manually override the subscription status.

**Headers:** `Authorization: Bearer <token>`

**Request Body**

```json
{
  "status": "active",
  "reason": "Manual reactivation by admin"
}
```

| `status` values |
| --------------- |
| `trial`         |
| `active`        |
| `past_due`      |
| `cancelled`     |
| `expired`       |

**Response `200`** — Updated subscription detail object

---

### PATCH `/api/v1/superadmin/subscriptions/{company_id}/update-seats`

Adjust the seat count for a subscription.

**Headers:** `Authorization: Bearer <token>`

**Request Body**

```json
{
  "seat_count": 100,
  "billable_seats": 100
}
```

| Field            | Type    | Required | Notes                                                           |
| ---------------- | ------- | -------- | --------------------------------------------------------------- |
| `seat_count`     | int ≥ 1 | Yes      |                                                                 |
| `billable_seats` | int ≥ 1 | No       | If omitted, calculated as `max(seat_count, plan.minimum_seats)` |

**Response `200`** — Updated subscription detail object

---

### PATCH `/api/v1/superadmin/subscriptions/{company_id}/update-ai-limit`

Override the AI query limit for the current billing month.

**Headers:** `Authorization: Bearer <token>`

**Request Body**

```json
{
  "queries_limit": 2000,
  "extra_queries": 500
}
```

| Field           | Type    | Required | Notes                            |
| --------------- | ------- | -------- | -------------------------------- |
| `queries_limit` | int ≥ 0 | Yes      | New monthly AI query limit       |
| `extra_queries` | int ≥ 0 | No       | Override extra purchased queries |

**Response `200`** — Updated subscription detail object

---

### DELETE `/api/v1/superadmin/subscriptions/{company_id}`

Permanently delete a company's subscription record.

**Headers:** `Authorization: Bearer <token>`

**Response `200`**

```json
{
  "success": true,
  "message": "Subscription deleted successfully"
}
```

**Error:** `404` — No subscription found

---

## Plan Management

### GET `/api/v1/superadmin/plans`

List all subscription plans.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `include_inactive` | bool | `false` | Include deactivated plans |

**Response `200`**

```json
[
  {
    "id": "uuid-here",
    "name": "Starter",
    "plan_key": "starter",
    "price_per_user_monthly": "49.00",
    "price_per_user_yearly": "39.00",
    "minimum_seats": 5,
    "ai_queries_limit": 500,
    "features": {
      "attendance": true,
      "leaves": true,
      "ai_chat": false
    },
    "is_active": true,
    "created_at": "2025-01-01T00:00:00"
  }
]
```

---

### POST `/api/v1/superadmin/plans`

Create a new subscription plan.

**Headers:** `Authorization: Bearer <token>`

**Request Body**

```json
{
  "name": "Enterprise",
  "plan_key": "enterprise",
  "price_per_user_monthly": "199.00",
  "price_per_user_yearly": "159.00",
  "minimum_seats": 20,
  "ai_queries_limit": 5000,
  "features": {
    "attendance": true,
    "leaves": true,
    "ai_chat": true,
    "custom_reports": true
  },
  "is_active": true
}
```

| Field                    | Type        | Required | Notes                              |
| ------------------------ | ----------- | -------- | ---------------------------------- |
| `name`                   | string      | Yes      | Must be unique                     |
| `plan_key`               | string      | Yes      | Must be unique (e.g. `enterprise`) |
| `price_per_user_monthly` | decimal ≥ 0 | Yes      |                                    |
| `price_per_user_yearly`  | decimal ≥ 0 | Yes      |                                    |
| `minimum_seats`          | int ≥ 1     | No       | Default: 1                         |
| `ai_queries_limit`       | int ≥ 0     | No       | Default: 0                         |
| `features`               | object      | No       | Arbitrary feature flags            |
| `is_active`              | bool        | No       | Default: `true`                    |

**Response `201`** — Created plan object

**Error:** `400` — Plan with same name or key already exists

---

### PATCH `/api/v1/superadmin/plans/{plan_id}`

Update an existing subscription plan.

**Headers:** `Authorization: Bearer <token>`

**Path Parameter:** `plan_id` (UUID string)

**Request Body** (all fields optional)

```json
{
  "name": "Enterprise Plus",
  "price_per_user_monthly": "219.00",
  "price_per_user_yearly": "175.00",
  "minimum_seats": 25,
  "ai_queries_limit": 10000,
  "features": {
    "custom_reports": true,
    "sso": true
  },
  "is_active": true
}
```

**Response `200`** — Updated plan object

**Error Responses**
| Status | Description |
|--------|-------------|
| 400 | Invalid UUID format |
| 404 | Plan not found |

---

### DELETE `/api/v1/superadmin/plans/{plan_id}`

Delete a subscription plan. Fails if any active or trial subscriptions use it.

**Headers:** `Authorization: Bearer <token>`

**Path Parameter:** `plan_id` (UUID string)

**Response `200`**

```json
{
  "success": true,
  "message": "Plan deleted successfully"
}
```

**Error Responses**
| Status | Description |
|--------|-------------|
| 400 | Plan has active subscriptions — deactivate it instead |
| 400 | Invalid UUID format |
| 404 | Plan not found |

---

## AI Usage Tracking

### GET `/api/v1/superadmin/ai-usage`

Platform-wide AI usage across all companies for a given month.
Sorted by highest token consumption — shows which company is using the most AI.

**Headers:** `Authorization: Bearer <superadmin-token>`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `year` | int | current year | Year to query |
| `month` | int | current month | Month (1–12) |

**Response `200`**

```json
{
  "period": "2025-04",
  "total_companies_active": 8,
  "platform_total_queries": 1842,
  "platform_total_tokens": 924800,
  "companies": [
    {
      "company_id": 3,
      "company_name": "TechCorp Pvt Ltd",
      "total_queries": 620,
      "total_tokens": 312000,
      "queries_limit": 1000,
      "queries_used": 620,
      "queries_remaining": 380,
      "utilisation_pct": 62.0,
      "last_used": "2025-04-11T14:32:00"
    },
    {
      "company_id": 1,
      "company_name": "Acme Corp",
      "total_queries": 142,
      "total_tokens": 71800,
      "queries_limit": 500,
      "queries_used": 142,
      "queries_remaining": 358,
      "utilisation_pct": 28.4,
      "last_used": "2025-04-10T09:12:00"
    }
  ]
}
```

---

### GET `/api/v1/superadmin/ai-usage/{company_id}`

Per-user AI usage breakdown for a specific company.
SuperAdmin can see exactly which employee or admin is consuming the most tokens.

**Headers:** `Authorization: Bearer <superadmin-token>`

**Path Parameter:** `company_id` (int)

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `year` | int | current year | Year to query |
| `month` | int | current month | Month (1–12) |

**Response `200`**

```json
{
  "company_id": 3,
  "company_name": "TechCorp Pvt Ltd",
  "period": "2025-04",
  "queries_used": 620,
  "queries_limit": 1000,
  "queries_remaining": 380,
  "total_tokens_this_month": 312000,
  "users": [
    {
      "user_id": 12,
      "user_name": "Ravi Kumar",
      "email": "ravi@techcorp.com",
      "role": "admin",
      "total_queries": 380,
      "total_tokens": 192000,
      "last_used": "2025-04-11T14:32:00"
    },
    {
      "user_id": 18,
      "user_name": "Priya Sharma",
      "email": "priya@techcorp.com",
      "role": "employee",
      "total_queries": 240,
      "total_tokens": 120000,
      "last_used": "2025-04-11T10:05:00"
    }
  ]
}
```

**Error:** `404` — Company not found

---

### GET `/api/v1/superadmin/ai-usage/{company_id}/history`

Month-by-month AI usage history for a company. Useful for spotting usage trends or sudden spikes.

**Headers:** `Authorization: Bearer <superadmin-token>`

**Path Parameter:** `company_id` (int)

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `months` | int | 6 | Number of past months (1–24) |

**Response `200`**

```json
{
  "company_id": 3,
  "company_name": "TechCorp Pvt Ltd",
  "months_included": 6,
  "history": [
    {
      "period": "2024-11",
      "year": 2024,
      "month": 11,
      "queries_used": 210,
      "queries_limit": 1000,
      "tokens_used": 105600,
      "active_users": 4
    },
    {
      "period": "2024-12",
      "year": 2024,
      "month": 12,
      "queries_used": 380,
      "queries_limit": 1000,
      "tokens_used": 191200,
      "active_users": 7
    },
    {
      "period": "2025-04",
      "year": 2025,
      "month": 4,
      "queries_used": 620,
      "queries_limit": 1000,
      "tokens_used": 312000,
      "active_users": 9
    }
  ]
}
```

**Error:** `404` — Company not found

---

## Error Response Format

All errors follow this structure:

```json
{
  "success": false,
  "message": "Human-readable error description",
  "error_code": "MACHINE_READABLE_CODE"
}
```

Common HTTP status codes:
| Status | Meaning |
|--------|---------|
| 400 | Bad request / validation error |
| 401 | Not authenticated or invalid/expired token |
| 403 | Forbidden (inactive account) |
| 404 | Resource not found |

---

## Quick Reference

| Method | Endpoint                                                 | Description                            |
| ------ | -------------------------------------------------------- | -------------------------------------- |
| POST   | `/superadmin/login`                                      | Login                                  |
| GET    | `/superadmin/me`                                         | Get current admin profile              |
| GET    | `/superadmin/stats`                                      | Platform statistics                    |
| GET    | `/superadmin/companies`                                  | List all companies                     |
| GET    | `/superadmin/companies/{id}`                             | Company detail                         |
| PATCH  | `/superadmin/companies/{id}`                             | Update company                         |
| DELETE | `/superadmin/companies/{id}`                             | Permanently delete company + all data  |
| GET    | `/superadmin/subscriptions`                              | List all subscriptions                 |
| GET    | `/superadmin/subscriptions/{company_id}`                 | Get company subscription               |
| POST   | `/superadmin/subscriptions/{company_id}`                 | Create subscription                    |
| PATCH  | `/superadmin/subscriptions/{company_id}/extend`          | Extend end date                        |
| PATCH  | `/superadmin/subscriptions/{company_id}/change-plan`     | Change plan                            |
| PATCH  | `/superadmin/subscriptions/{company_id}/change-status`   | Change status                          |
| PATCH  | `/superadmin/subscriptions/{company_id}/update-seats`    | Update seats                           |
| PATCH  | `/superadmin/subscriptions/{company_id}/update-ai-limit` | Update AI limit                        |
| DELETE | `/superadmin/subscriptions/{company_id}`                 | Delete subscription                    |
| GET    | `/superadmin/plans`                                      | List plans                             |
| POST   | `/superadmin/plans`                                      | Create plan                            |
| PATCH  | `/superadmin/plans/{plan_id}`                            | Update plan                            |
| DELETE | `/superadmin/plans/{plan_id}`                            | Delete plan                            |
| GET    | `/superadmin/ai-usage`                                   | Platform-wide AI usage (all companies) |
| GET    | `/superadmin/ai-usage/{company_id}`                      | Per-user AI usage for a company        |
| GET    | `/superadmin/ai-usage/{company_id}/history`              | Month-by-month usage history           |
